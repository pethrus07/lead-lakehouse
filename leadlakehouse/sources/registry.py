"""Registro de fontes. As implementações se registram aqui; o orquestrador consulta.

As fontes concretas (CNPJ, Google Maps, OpenStreetMap, Instagram, ...) entram na F1/F2.
Este registro já existe para que adicionar fonte seja: escrever o módulo + registrar.
"""

from __future__ import annotations

from ..domain.models import Fonte
from ..domain.sources import DiscoverySource, EnrichmentSource

_DISCOVERY: dict[Fonte, DiscoverySource] = {}
_ENRICHMENT: dict[Fonte, EnrichmentSource] = {}


def registrar_discovery(fonte: Fonte, instancia: DiscoverySource) -> None:
    _DISCOVERY[fonte] = instancia


def registrar_enrichment(fonte: Fonte, instancia: EnrichmentSource) -> None:
    _ENRICHMENT[fonte] = instancia


def discovery_disponiveis() -> dict[Fonte, DiscoverySource]:
    return dict(_DISCOVERY)


def enrichment_disponiveis() -> dict[Fonte, EnrichmentSource]:
    return dict(_ENRICHMENT)


def resumo() -> list[dict]:
    """Lista legível das fontes registradas (usada pela CLI `llh fontes`)."""
    linhas = []
    for fonte, inst in _DISCOVERY.items():
        c = inst.capacidades
        linhas.append({
            "fonte": fonte.value, "papel": "descoberta",
            "browser": c.requer_browser, "pago": c.requer_pago, "tos_ok": c.respeita_tos,
        })
    for fonte, inst in _ENRICHMENT.items():
        c = inst.capacidades
        linhas.append({
            "fonte": fonte.value, "papel": "enriquecimento",
            "browser": c.requer_browser, "pago": c.requer_pago, "tos_ok": c.respeita_tos,
        })
    return linhas
