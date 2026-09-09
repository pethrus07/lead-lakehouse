"""Registra as fontes/enriquecedores disponíveis. Chamado pela CLI e pela UI.

Adicionar uma fonte nova = implementá-la e acrescentar uma linha aqui.
"""

from __future__ import annotations

from ..config import settings
from ..domain.models import Fonte
from . import registry

# Guarda de idempotência: a CLI e a UI podem chamar isto mais de uma vez no mesmo processo,
# e registrar de novo trocaria as instâncias que já estão em uso.
_carregado = False


def registrar_todas() -> None:
    global _carregado
    if _carregado:
        return

    # ── Descoberta ──────────────────────────────────────────────
    from .google_maps import GoogleMapsSource
    from .openstreetmap import OpenStreetMapSource

    registry.registrar_discovery(Fonte.OPENSTREETMAP, OpenStreetMapSource())
    registry.registrar_discovery(Fonte.GOOGLE_MAPS, GoogleMapsSource())

    # ── Enriquecimento ──────────────────────────────────────────
    from ..enrichment.cnpj_enrich import CnpjEnricher
    from ..enrichment.site_visitor import SiteVisitorEnricher

    registry.registrar_enrichment(Fonte.SITE, SiteVisitorEnricher())
    registry.registrar_enrichment(Fonte.CNPJ, CnpjEnricher())

    # ── Fontes que exigem chave paga: só se configuradas (custo zero por padrão) ─
    if settings.google_places_api_key:
        from .google_places import GooglePlacesSource
        registry.registrar_discovery(Fonte.GOOGLE_PLACES, GooglePlacesSource())

    _carregado = True
