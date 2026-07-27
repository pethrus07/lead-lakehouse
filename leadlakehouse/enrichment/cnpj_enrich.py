"""Enriquecimento por CNPJ via minhareceita.org (dados abertos da Receita, grátis).

Adiciona razão social, CNAE, situação cadastral e data de abertura (→ sinal 'negócio novo').
"""

from __future__ import annotations

from datetime import date

import httpx

from ..domain.identity import so_digitos
from ..domain.models import Business, Fonte
from ..domain.sources import CapacidadesFonte

BASE = "https://minhareceita.org"


def aplicar_cnpj(b: Business, d: dict) -> Business:
    """Preenche o negócio com os dados da Receita. Puro/testável."""
    if not b.nome:
        b.nome = d.get("razao_social") or d.get("nome_fantasia")
    if not b.cnae and d.get("cnae_fiscal"):
        b.cnae = str(d["cnae_fiscal"])
    if not b.situacao_cnpj:
        b.situacao_cnpj = d.get("descricao_situacao_cadastral")
    if not b.data_abertura and d.get("data_inicio_atividade"):
        try:
            b.data_abertura = date.fromisoformat(d["data_inicio_atividade"][:10])
        except (ValueError, TypeError):
            pass
    if not b.municipio and d.get("municipio"):
        b.municipio = d["municipio"]
    if not b.uf and d.get("uf"):
        b.uf = d["uf"]
    if not b.email and d.get("email"):
        b.email = d["email"]
    if not b.telefone and d.get("ddd_telefone_1"):
        b.telefone = d["ddd_telefone_1"]
    b.fontes = set(b.fontes) | {Fonte.CNPJ}
    return b


class CnpjEnricher:
    capacidades = CapacidadesFonte(
        fonte=Fonte.CNPJ, enriquecimento=True, requer_pago=False, respeita_tos=True
    )

    def __init__(self, base: str = BASE, timeout: float = 15.0):
        self.base = base
        self.timeout = timeout

    async def enriquecer(self, b: Business) -> Business:
        cnpj = so_digitos(b.cnpj)
        if len(cnpj) != 14:
            return b
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.get(f"{self.base}/{cnpj}")
                if r.status_code != 200:
                    return b
                dados = r.json()
        except Exception:
            return b
        return aplicar_cnpj(b, dados)
