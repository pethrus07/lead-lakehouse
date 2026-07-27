"""Fonte OpenStreetMap via Overpass API. DiscoverySource — livre, sem token, sem ToS.

Descobre POIs por categoria dentro de um município (por nome) ou raio (lat/lng).
"""

from __future__ import annotations

import asyncio
import unicodedata
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import structlog

from ..domain.icp import ICP
from ..domain.models import Business, Fonte
from ..domain.sources import CapacidadesFonte

log = structlog.get_logger()

# Mirrors públicos do Overpass — fallback quando um rate-limita (429) ou cai (504).
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OVERPASS_URL = OVERPASS_MIRRORS[0]
# Overpass.de rejeita (406) requisições sem User-Agent identificável.
_HEADERS = {"User-Agent": "lead-lakehouse/1.0 (prospeccao B2B; +github.com/pethrus07)"}

# nicho (normalizado) → tags OSM (chave, valor)
NICHO_OSM: dict[str, list[tuple[str, str]]] = {
    "salao": [("shop", "hairdresser"), ("shop", "beauty")],
    "salao de beleza": [("shop", "hairdresser"), ("shop", "beauty")],
    "cabeleireiro": [("shop", "hairdresser")],
    "barbearia": [("shop", "hairdresser")],
    "estetica": [("shop", "beauty")],
    "restaurante": [("amenity", "restaurant")],
    "lanchonete": [("amenity", "fast_food")],
    "pizzaria": [("amenity", "restaurant")],
    "hamburgueria": [("amenity", "fast_food")],
    "cafe": [("amenity", "cafe")],
    "padaria": [("shop", "bakery")],
    "petshop": [("shop", "pet")],
    "pet": [("shop", "pet")],
    "veterinario": [("amenity", "veterinary")],
    "farmacia": [("amenity", "pharmacy")],
    "mecanica": [("shop", "car_repair")],
    "oficina": [("shop", "car_repair")],
    "academia": [("leisure", "fitness_centre")],
    "mercado": [("shop", "supermarket"), ("shop", "convenience")],
    "supermercado": [("shop", "supermarket")],
    "dentista": [("amenity", "dentist")],
    "odonto": [("amenity", "dentist")],
    "clinica": [("amenity", "clinic")],
    "hotel": [("tourism", "hotel")],
    "pousada": [("tourism", "guest_house")],
    "loja de roupas": [("shop", "clothes")],
    "roupas": [("shop", "clothes")],
    "otica": [("shop", "optician")],
    "floricultura": [("shop", "florist")],
}


def _norm(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    return t.lower().strip()


def tags_para_nicho(nicho: str) -> list[tuple[str, str]]:
    n = _norm(nicho)
    if n in NICHO_OSM:
        return NICHO_OSM[n]
    for chave, tags in NICHO_OSM.items():
        if chave in n or n in chave:
            return tags
    return []   # sem mapeamento → cai no fallback por nome


def montar_query(icp: ICP, nicho: str) -> str:
    r = icp.regiao
    tags = tags_para_nicho(nicho)
    filtros: list[str] = []
    if tags:
        for chave, valor in tags:
            filtros.append(f'["{chave}"="{valor}"]')
    else:
        filtros.append(f'["name"~"{nicho}",i]')

    if r.lat is not None and r.lng is not None:
        raio = int((r.raio_km or 5) * 1000)
        alvo = f"(around:{raio},{r.lat},{r.lng})"
        corpo = "".join(
            f"  node{f}{alvo};\n  way{f}{alvo};\n" for f in filtros
        )
        return f"[out:json][timeout:60];\n(\n{corpo});\nout center tags {icp.limite};"

    # por nome de município (área administrativa)
    municipio = (r.municipio or "").replace('"', "")
    corpo = "".join(
        f"  node(area.a){f};\n  way(area.a){f};\n" for f in filtros
    )
    return (
        f'[out:json][timeout:60];\n'
        f'area["name"="{municipio}"]["admin_level"~"8|9|10"]->.a;\n'
        f"(\n{corpo});\nout center tags {icp.limite};"
    )


def elemento_para_business(el: dict, icp: ICP) -> Business | None:
    """Mapeia um elemento Overpass → Business. Puro/testável."""
    tags = el.get("tags", {})
    nome = tags.get("name")
    if not nome:
        return None

    site = tags.get("website") or tags.get("contact:website")
    telefone = tags.get("phone") or tags.get("contact:phone")
    redes = {}
    for rede in ("instagram", "facebook", "youtube"):
        v = tags.get(f"contact:{rede}") or tags.get(rede)
        if v:
            redes[rede] = v

    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lng = el.get("lon") or (el.get("center") or {}).get("lon")

    endereco = " ".join(
        p for p in [tags.get("addr:street"), tags.get("addr:housenumber")] if p
    ) or None

    return Business(
        nome=nome,
        categoria=tags.get("shop") or tags.get("amenity") or tags.get("leisure"),
        telefone=telefone,
        email=tags.get("email") or tags.get("contact:email"),
        site=site,
        tem_site=bool(site),
        redes_sociais=redes,
        lat=lat,
        lng=lng,
        municipio=tags.get("addr:city") or icp.regiao.municipio,
        uf=icp.regiao.uf,
        endereco=endereco,
        fontes={Fonte.OPENSTREETMAP},
        url_origem={Fonte.OPENSTREETMAP.value: f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}"},
        raw={"openstreetmap": {"id": el.get("id"), "type": el.get("type"), "tags": tags}},
        coletado_em=datetime.now(UTC),
    )


class OpenStreetMapSource:
    capacidades = CapacidadesFonte(
        fonte=Fonte.OPENSTREETMAP,
        descoberta=True,
        filtros_nativos={"municipio"},
        requer_browser=False,
        requer_pago=False,
        respeita_tos=True,
    )

    def __init__(self, mirrors: list[str] | None = None, timeout: float = 90.0,
                 tentativas: int = 3):
        self.mirrors = mirrors or OVERPASS_MIRRORS
        self.timeout = timeout
        self.tentativas = tentativas

    async def _consultar(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Consulta o Overpass com retry + fallback entre mirrors. Loga o motivo em falha."""
        ultimo_erro = ""
        for tentativa in range(self.tentativas):
            url = self.mirrors[tentativa % len(self.mirrors)]
            try:
                resp = await client.post(url, data={"data": query})
                if resp.status_code in (429, 504):   # rate-limit / gateway timeout
                    ultimo_erro = f"{resp.status_code} em {url}"
                    await asyncio.sleep(2 * (tentativa + 1))
                    continue
                resp.raise_for_status()
                return resp.json().get("elements", [])
            except Exception as e:  # noqa: BLE001
                ultimo_erro = f"{type(e).__name__} em {url}: {e}"
                await asyncio.sleep(1.5 * (tentativa + 1))
        log.warning("overpass_falhou", erro=ultimo_erro)
        return []

    async def descobrir(self, icp: ICP) -> AsyncIterator[Business]:
        restante = icp.limite
        async with httpx.AsyncClient(timeout=self.timeout, headers=_HEADERS) as client:
            for nicho in (icp.nicho or [""]):
                if restante <= 0:
                    break
                query = montar_query(icp, nicho)
                elementos = await self._consultar(client, query)
                log.info("overpass_ok", nicho=nicho, elementos=len(elementos))
                for el in elementos:
                    if restante <= 0:
                        break
                    b = elemento_para_business(el, icp)
                    if b:
                        yield b
                        restante -= 1
