"""Orquestração de uma prospecção: coleta → dedup → enriquece → filtra → pontua → persiste."""

from __future__ import annotations

import structlog

from ..domain.icp import ICP
from ..domain.identity import deduplicar, normalizar_nome
from ..domain.models import Business, Lead, LeadStatus
from ..domain.scoring import pontuar
from ..infra.db import repository as repo
from ..infra.db.base import Session
from ..pipeline.bronze import salvar_bronze
from ..sources.registry import discovery_disponiveis, enrichment_disponiveis

log = structlog.get_logger()


def _slug(txt: str | None) -> str | None:
    n = normalizar_nome(txt)
    return n.replace(" ", "-") if n else None


def gerar_tags(b: Business, icp: ICP, nivel: str) -> list[str]:
    tags = ["lead-lakehouse", f"icp-{_slug(icp.nome)}", f"oportunidade-{nivel}"]
    if icp.nicho:
        tags.append(f"nicho-{_slug(icp.nicho[0])}")
    if b.municipio:
        tags.append(f"cidade-{_slug(b.municipio)}")
    for s in b.sinais:
        tags.append(f"sinal-{str(s.tipo).replace('_', '-')}")
    if not b.tem_site:
        tags.append("sem-site")
    return list(dict.fromkeys(t for t in tags if t and not t.endswith("-None")))


async def coletar(icp: ICP) -> list[Business]:
    """Roda as fontes de descoberta aplicáveis ao ICP e salva o bronze de cada uma."""
    disponiveis = discovery_disponiveis()
    escolhidas = {f: s for f, s in disponiveis.items() if not icp.fontes or f in icp.fontes}
    if not escolhidas:
        log.warning("nenhuma_fonte_descoberta", fontes_pedidas=[str(f) for f in icp.fontes])
        return []

    brutos: list[Business] = []
    for fonte, source in escolhidas.items():
        coletados: list[Business] = []
        try:
            async for b in source.descobrir(icp):
                coletados.append(b)
        except Exception as e:  # noqa: BLE001
            log.error("erro_fonte", fonte=str(fonte), erro=str(e))
        if coletados:
            caminho = salvar_bronze(coletados, fonte, query=" ".join(icp.nicho))
            log.info("fonte_coletou", fonte=str(fonte), n=len(coletados), bronze=caminho)
        brutos.extend(coletados)
    return brutos


async def enriquecer(negocios: list[Business], icp: ICP) -> list[Business]:
    """Passa cada negócio pelos enriquecedores registrados (adicionam sinais/dados)."""
    enrichers = enrichment_disponiveis()
    if not enrichers:
        return negocios
    out: list[Business] = []
    for b in negocios:
        for fonte, source in enrichers.items():
            try:
                b = await source.enriquecer(b)
            except Exception as e:  # noqa: BLE001
                log.warning("erro_enriquecimento", fonte=str(fonte), erro=str(e))
        out.append(b)
    return out


async def prospectar(
    icp: ICP, persistir: bool = True, enriquecer_flag: bool = True
) -> list[Lead]:
    brutos = await coletar(icp)
    negocios = deduplicar(brutos)
    log.info("dedup", brutos=len(brutos), unicos=len(negocios))

    if enriquecer_flag:
        negocios = await enriquecer(negocios, icp)

    leads: list[Lead] = []
    for b in negocios:
        if not icp.filtros.aprova(b):
            continue
        score = pontuar(b, icp)
        tags = gerar_tags(b, icp, str(score.nivel))
        leads.append(Lead(business=b, icp_nome=icp.nome, score=score, tags=tags,
                          status=LeadStatus.NOVO))

    leads.sort(key=lambda ld: ld.score.valor, reverse=True)
    log.info("prospeccao_ok", leads=len(leads))

    if persistir and leads:
        _persistir(icp, leads, descobertos=len(brutos))
    return leads


def _persistir(icp: ICP, leads: list[Lead], descobertos: int) -> None:
    with Session() as session:
        run = repo.abrir_run(session, icp.nome)
        novos = 0
        for lead in leads:
            b_orm = repo.upsert_business(session, lead.business)
            l_orm = repo.salvar_lead(session, lead, b_orm)
            if l_orm.id is not None:
                novos += 1
        repo.fechar_run(session, run, descobertos=descobertos, novos=len(leads), erros=0)
        session.commit()
