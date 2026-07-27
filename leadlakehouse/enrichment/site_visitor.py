"""Enriquecimento pela visita ao site: e-mail, WhatsApp, SSL, responsividade, velocidade.

Cada achado vira um Sinal de oportunidade (site sem SSL / não responsivo / lento).
"""

from __future__ import annotations

import re
import time

import httpx

from ..domain.models import Business, Fonte, Sinal, TipoSinal
from ..domain.sources import CapacidadesFonte

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
WHATSAPP_RE = re.compile(r"(wa\.me/|api\.whatsapp\.com|whatsapp://|web\.whatsapp\.com)")
LIMITE_LENTO_S = 3.0
_UA = {"User-Agent": "Mozilla/5.0 (compatible; lead-lakehouse/1.0)"}


def analisar_html(html: str, sem_ssl: bool, elapsed: float | None) -> tuple[list[Sinal], dict]:
    """Deriva sinais + campos (email/whatsapp) a partir do HTML. Puro/testável."""
    sinais: list[Sinal] = []
    extras: dict = {}

    if sem_ssl:
        sinais.append(Sinal(tipo=TipoSinal.SITE_SEM_SSL, fonte=Fonte.SITE))
    if "viewport" not in html.lower():
        sinais.append(Sinal(tipo=TipoSinal.SITE_NAO_RESPONSIVO, fonte=Fonte.SITE))
    if elapsed is not None and elapsed > LIMITE_LENTO_S:
        sinais.append(Sinal(tipo=TipoSinal.SITE_LENTO, fonte=Fonte.SITE, valor=round(elapsed, 2)))

    m = EMAIL_RE.search(html)
    if m:
        extras["email"] = m.group(0)
    if WHATSAPP_RE.search(html):
        extras["tem_whatsapp"] = True
    return sinais, extras


class SiteVisitorEnricher:
    capacidades = CapacidadesFonte(
        fonte=Fonte.SITE, enriquecimento=True, requer_pago=False, respeita_tos=True
    )

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout

    async def _buscar(self, url: str) -> tuple[str | None, bool, float | None]:
        """Retorna (html, sem_ssl, elapsed). Se a verificação SSL falhar, tenta sem verificar."""
        for verify, marca_sem_ssl in ((True, False), (False, True)):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=True, verify=verify, headers=_UA
                ) as c:
                    t0 = time.perf_counter()
                    r = await c.get(url)
                    elapsed = time.perf_counter() - t0
                    sem_ssl = marca_sem_ssl or str(r.url).startswith("http://")
                    return (r.text or ""), sem_ssl, elapsed
            except (httpx.ConnectError, httpx.ReadError):
                continue  # pode ser certificado inválido → tenta sem verificar
            except Exception:
                return None, False, None
        return None, False, None

    async def enriquecer(self, b: Business) -> Business:
        if not b.site:
            return b
        url = b.site if b.site.startswith("http") else f"https://{b.site}"
        html, sem_ssl, elapsed = await self._buscar(url)
        if html is None:
            return b

        sinais, extras = analisar_html(html, sem_ssl, elapsed)
        if not b.email and extras.get("email"):
            b.email = extras["email"]
        if extras.get("tem_whatsapp"):
            b.tem_whatsapp = True

        existentes = {s.tipo for s in b.sinais}
        b.sinais = b.sinais + [s for s in sinais if s.tipo not in existentes]
        b.fontes = set(b.fontes) | {Fonte.SITE}
        return b
