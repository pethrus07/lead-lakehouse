"""Contratos de fonte de dados. Adicionar uma fonte = implementar uma destas interfaces."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from .models import Business, Fonte

if TYPE_CHECKING:
    from .icp import ICP


class CapacidadesFonte(BaseModel):
    """Descreve o que uma fonte sabe fazer — o orquestrador usa p/ planejar."""

    fonte: Fonte
    descoberta: bool = False        # encontra negócios a partir de um ICP?
    enriquecimento: bool = False    # adiciona sinais a um negócio já conhecido?
    filtros_nativos: set[str] = Field(default_factory=set)  # filtros resolvidos na origem
    requer_browser: bool = False
    requer_pago: bool = False       # depende de API paga / proxy?
    respeita_tos: bool = True       # fonte oficial/aberta (sem violar ToS)?


@runtime_checkable
class DiscoverySource(Protocol):
    """Fonte de descoberta: dado um ICP, produz negócios."""

    capacidades: CapacidadesFonte

    def descobrir(self, icp: ICP) -> AsyncIterator[Business]:
        ...


@runtime_checkable
class EnrichmentSource(Protocol):
    """Fonte de enriquecimento: dado um negócio, devolve-o com mais sinais/dados."""

    capacidades: CapacidadesFonte

    async def enriquecer(self, negocio: Business) -> Business:
        ...
