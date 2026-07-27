"""Pontuação de oportunidade. Generaliza o antigo `score_digital` (0/1/2)."""

from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta

from .icp import ICP
from .models import Business, NivelOportunidade, Score, Sinal, TipoSinal

MESES_NEGOCIO_NOVO = 24
LIMITE_POUCAS_AVALIACOES = 10
NOTA_BAIXA_ABAIXO_DE = 3.5


def derivar_sinais(b: Business, ref: date | None = None) -> list[Sinal]:
    """Deriva sinais de oportunidade a partir dos campos do negócio.

    `ref` = data de referência p/ "negócio novo" (default: hoje). Explícito nos testes.
    """
    ref = ref or date.today()
    sinais: list[Sinal] = []

    if not b.tem_site:
        sinais.append(Sinal(tipo=TipoSinal.SEM_SITE))
        if b.redes_sociais:
            sinais.append(Sinal(tipo=TipoSinal.SO_REDES))

    if b.data_abertura is not None:
        if b.data_abertura >= ref - relativedelta(months=MESES_NEGOCIO_NOVO):
            sinais.append(Sinal(tipo=TipoSinal.NEGOCIO_NOVO, valor=b.data_abertura.isoformat()))

    if b.n_avaliacoes is not None and b.n_avaliacoes < LIMITE_POUCAS_AVALIACOES:
        sinais.append(Sinal(tipo=TipoSinal.POUCAS_AVALIACOES, valor=b.n_avaliacoes))

    if b.nota is not None and b.nota < NOTA_BAIXA_ABAIXO_DE:
        sinais.append(Sinal(tipo=TipoSinal.NOTA_BAIXA, valor=b.nota))

    if b.tem_whatsapp is True:
        sinais.append(Sinal(tipo=TipoSinal.TEM_WHATSAPP))
    elif b.tem_whatsapp is False:
        sinais.append(Sinal(tipo=TipoSinal.SEM_WHATSAPP))

    return sinais


def _nivel(valor: float, icp: ICP) -> NivelOportunidade:
    p = icp.pesos
    if valor >= p.limiar_alta:
        return NivelOportunidade.ALTA
    if valor >= p.limiar_media:
        return NivelOportunidade.MEDIA
    if valor >= p.limiar_baixa:
        return NivelOportunidade.BAIXA
    return NivelOportunidade.NENHUMA


def pontuar(b: Business, icp: ICP, ref: date | None = None) -> Score:
    """Combina sinais derivados + coletados (enriquecimento) e aplica os pesos do ICP."""
    derivados = derivar_sinais(b, ref)

    # dedup por tipo (Sinal.__eq__/__hash__ usam só o tipo); coletados têm prioridade
    por_tipo: dict[TipoSinal, Sinal] = {}
    for s in derivados + list(b.sinais):
        por_tipo[s.tipo] = s
    sinais = list(por_tipo.values())

    breakdown = {s.tipo.value: icp.pesos.peso(s.tipo) for s in sinais}
    valor = sum(breakdown.values())

    return Score(valor=valor, nivel=_nivel(valor, icp), sinais=sinais, breakdown=breakdown)
