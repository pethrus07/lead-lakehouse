"""Fonte Google Places API (oficial, PAGA). Só é registrada se houver chave configurada.

Fica pronta para o dia em que valer a pena pagar por dados estáveis; custo zero por padrão.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from ..config import settings
from ..domain.icp import ICP
from ..domain.models import Business, Fonte
from ..domain.sources import CapacidadesFonte

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELDS = (
    "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
    "places.websiteUri,places.rating,places.userRatingCount,places.location,"
    "places.primaryTypeDisplayName"
)


def _lugar_para_business(p: dict, icp: ICP) -> Business:
    loc = p.get("location", {})
    site = p.get("websiteUri")
    return Business(
        nome=(p.get("displayName") or {}).get("text"),
        categoria=(p.get("primaryTypeDisplayName") or {}).get("text"),
        telefone=p.get("nationalPhoneNumber"),
        site=site,
        tem_site=bool(site),
        nota=p.get("rating"),
        n_avaliacoes=p.get("userRatingCount"),
        lat=loc.get("latitude"),
        lng=loc.get("longitude"),
        endereco=p.get("formattedAddress"),
        municipio=icp.regiao.municipio,
        uf=icp.regiao.uf,
        fontes={Fonte.GOOGLE_PLACES},
        raw={"google_places": p},
        coletado_em=datetime.now(UTC),
    )


class GooglePlacesSource:
    capacidades = CapacidadesFonte(
        fonte=Fonte.GOOGLE_PLACES,
        descoberta=True,
        enriquecimento=True,
        requer_browser=False,
        requer_pago=True,
        respeita_tos=True,
    )

    def __init__(self):
        self.key = settings.google_places_api_key

    async def descobrir(self, icp: ICP) -> AsyncIterator[Business]:
        if not self.key:
            return
        r = icp.regiao
        local = " ".join(p for p in [r.municipio, r.uf] if p)
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key,
            "X-Goog-FieldMask": _FIELDS,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            for nicho in (icp.nicho or [""]):
                body = {"textQuery": f"{nicho} em {local}".strip(), "languageCode": "pt-BR",
                        "maxResultCount": min(icp.limite, 20)}
                try:
                    resp = await client.post(SEARCH_URL, headers=headers, json=body)
                    resp.raise_for_status()
                    lugares = resp.json().get("places", [])
                except Exception:
                    continue
                for p in lugares:
                    yield _lugar_para_business(p, icp)
