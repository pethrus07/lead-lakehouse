"""Fonte Google Maps (Playwright). DiscoverySource.

A extração viva do DOM (frágil, muda quando o Google mexe no HTML) fica isolada em
`_extrair_raw`. O mapeamento raw→Business é puro e testável (`raw_para_business`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from ..domain.icp import ICP
from ..domain.models import Business, Fonte
from ..domain.sources import CapacidadesFonte
from ..infra.browser import BrowserPool, atraso

_SOCIAIS = ("instagram", "facebook", "tiktok", "twitter", "linkedin", "youtube")


def _query_do_icp(icp: ICP, nicho: str) -> str:
    r = icp.regiao
    local = " ".join(p for p in [r.municipio, r.uf] if p)
    return f"{nicho} em {local}".strip() if local else nicho


def raw_para_business(raw: dict) -> Business:
    """Mapeia o dicionário extraído do Maps para um Business. Puro/testável."""
    redes = {}
    for href in raw.get("links", []):
        low = href.lower()
        for rede in _SOCIAIS:
            if rede in low and rede not in redes:
                redes[rede] = href
    tem_site = bool(raw.get("site"))
    raw_min = {k: v for k, v in raw.items() if k != "links"}  # não guarda a lista de hrefs
    return Business(
        nome=raw.get("nome"),
        categoria=raw.get("categoria"),
        telefone=raw.get("telefone"),
        site=raw.get("site"),
        tem_site=tem_site,
        redes_sociais=redes,
        nota=raw.get("nota"),
        n_avaliacoes=raw.get("n_avaliacoes"),
        municipio=raw.get("municipio"),
        uf=raw.get("uf"),
        endereco=raw.get("endereco"),
        lat=raw.get("lat"),
        lng=raw.get("lng"),
        fontes={Fonte.GOOGLE_MAPS},
        url_origem={Fonte.GOOGLE_MAPS.value: raw["url"]} if raw.get("url") else {},
        raw={"google_maps": raw_min},
        coletado_em=datetime.now(UTC),
    )


def _num(txt: str | None) -> float | None:
    if not txt:
        return None
    limpo = "".join(c for c in txt if c.isdigit() or c in ".,").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _inteiro(txt: str | None) -> int | None:
    if not txt:
        return None
    digitos = "".join(c for c in txt if c.isdigit())
    return int(digitos) if digitos else None


class GoogleMapsSource:
    """Descobre negócios no Google Maps a partir do nicho + região do ICP."""

    capacidades = CapacidadesFonte(
        fonte=Fonte.GOOGLE_MAPS,
        descoberta=True,
        enriquecimento=True,
        filtros_nativos=set(),   # filtramos em pós-processamento
        requer_browser=True,
        requer_pago=False,
        respeita_tos=False,      # scraping — usar com parcimônia
    )

    def __init__(self, headless: bool | None = None):
        self.headless = headless

    async def descobrir(self, icp: ICP) -> AsyncIterator[Business]:
        nichos = icp.nicho or [""]
        vistos: set[str] = set()
        restante = icp.limite

        async with BrowserPool(headless=self.headless) as pool:
            page = await pool.nova_pagina()
            for nicho in nichos:
                if restante <= 0:
                    break
                query = _query_do_icp(icp, nicho)
                links = await self._buscar_links(page, query, restante)
                for url in links:
                    if url in vistos or restante <= 0:
                        continue
                    vistos.add(url)
                    try:
                        raw = await self._extrair_raw(page, url)
                        raw["municipio"] = raw.get("municipio") or icp.regiao.municipio
                        raw["uf"] = raw.get("uf") or icp.regiao.uf
                        yield raw_para_business(raw)
                        restante -= 1
                    except Exception:
                        # Ficha que não abre ou mudou de layout não derruba a coleta inteira.
                        pass
                    await atraso()

    async def _buscar_links(self, page, query: str, limite: int) -> list[str]:
        import urllib.parse

        url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}?hl=pt-BR"
        await page.goto(url, wait_until="domcontentloaded")
        await atraso()
        # aceita consentimento se aparecer
        try:
            btn = page.locator('button:has-text("Aceitar"), button:has-text("Accept")').first
            if await btn.count():
                await btn.click(timeout=3000)
        except Exception:
            pass

        try:
            await page.wait_for_selector('div[role="feed"]', timeout=10000)
        except Exception:
            return []

        feed = page.locator('div[role="feed"]')
        anterior, estavel = 0, 0
        while estavel < 5:
            cards = page.locator('div[role="feed"] a[href*="/maps/place"]')
            n = await cards.count()
            if n >= limite:
                break
            estavel = estavel + 1 if n == anterior else 0
            anterior = n
            await feed.evaluate("el => el.scrollBy(0, 1200)")
            await atraso()

        hrefs = await page.locator('div[role="feed"] a[href*="/maps/place"]').evaluate_all(
            "els => els.map(e => e.href)"
        )
        # dedup preservando ordem
        out, seen = [], set()
        for h in hrefs:
            if h not in seen:
                seen.add(h)
                out.append(h)
        return out[:limite]

    async def _extrair_raw(self, page, url: str) -> dict:
        await page.goto(url, wait_until="domcontentloaded")
        await atraso()
        raw: dict = {"url": url}

        async def txt(sel: str) -> str | None:
            try:
                loc = page.locator(sel).first
                if await loc.count():
                    return (await loc.inner_text()).strip()
            except Exception:
                pass
            return None

        async def attr(sel: str, nome_attr: str) -> str | None:
            try:
                loc = page.locator(sel).first
                if await loc.count():
                    return await loc.get_attribute(nome_attr)
            except Exception:
                pass
            return None

        raw["nome"] = await txt("h1")
        raw["categoria"] = await txt('button[jsaction*="category"]')
        raw["endereco"] = await attr('button[data-item-id="address"]', "aria-label")
        # telefone: data-item-id começa com "phone:tel:"
        tel_aria = await attr('button[data-item-id^="phone"]', "aria-label")
        raw["telefone"] = tel_aria.split(":", 1)[-1].strip() if tel_aria else None
        raw["site"] = await attr('a[data-item-id="authority"]', "href")

        nota_aria = await attr('div.F7nice span[aria-hidden="true"]', "aria-hidden")
        raw["nota"] = _num(await txt('div.F7nice span[aria-hidden="true"]') or nota_aria)
        raw["n_avaliacoes"] = _inteiro(await txt('div.F7nice span[aria-label*="avali"]'))

        # coords a partir da URL (…!3dLAT!4dLNG…)
        import re

        m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
        if m:
            raw["lat"], raw["lng"] = float(m.group(1)), float(m.group(2))

        raw["links"] = await page.locator('a[href^="http"]').evaluate_all(
            "els => els.map(e => e.href)"
        )
        return raw
