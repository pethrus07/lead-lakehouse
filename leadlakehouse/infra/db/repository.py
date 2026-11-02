"""Repositório — persiste negócios (silver) e leads (gold) no Postgres. Upsert idempotente."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as SASession

from ...config import settings
from ...domain.identity import chave_identidade
from ...domain.models import Business, Lead
from .models import BusinessORM, LeadORM, RunORM


def _business_para_dict(b: Business) -> dict:
    return {
        "cnpj": b.cnpj,
        "nome": b.nome,
        "nome_norm": b.nome_norm,
        "telefone": b.telefone,
        "telefone_e164": b.telefone_e164,
        "email": b.email,
        "site": b.site,
        "tem_site": b.tem_site,
        "tem_whatsapp": b.tem_whatsapp,
        "redes_sociais": b.redes_sociais,
        "categoria": b.categoria,
        "cnae": b.cnae,
        "nota": b.nota,
        "n_avaliacoes": b.n_avaliacoes,
        "data_abertura": b.data_abertura,
        "situacao_cnpj": b.situacao_cnpj,
        "lat": b.lat,
        "lng": b.lng,
        "municipio": b.municipio,
        "uf": b.uf,
        "endereco": b.endereco,
        "fontes": [str(f) for f in b.fontes],
        "sinais": [s.model_dump(mode="json") for s in b.sinais],
        "raw": b.raw,
        "coletado_em": b.coletado_em,
    }


def upsert_business(session: SASession, b: Business, tenant_id: str | None = None) -> BusinessORM:
    tid = tenant_id or settings.tenant_id
    chave = chave_identidade(b)
    orm = session.scalar(
        select(BusinessORM).where(
            BusinessORM.tenant_id == tid, BusinessORM.chave_identidade == chave
        )
    )
    dados = _business_para_dict(b)
    if orm is None:
        orm = BusinessORM(tenant_id=tid, chave_identidade=chave, **dados)
        session.add(orm)
    else:
        for k, v in dados.items():
            setattr(orm, k, v)
    session.flush()
    return orm


def salvar_lead(
    session: SASession, lead: Lead, business_orm: BusinessORM, tenant_id: str | None = None
) -> LeadORM:
    tid = tenant_id or settings.tenant_id
    orm = session.scalar(
        select(LeadORM).where(
            LeadORM.tenant_id == tid,
            LeadORM.business_id == business_orm.id,
            LeadORM.icp_nome == lead.icp_nome,
        )
    )
    if orm is None:
        orm = LeadORM(tenant_id=tid, business_id=business_orm.id, icp_nome=lead.icp_nome)
        session.add(orm)
    orm.score = lead.score.valor
    orm.nivel = str(lead.score.nivel)
    orm.tags = lead.tags
    orm.breakdown = lead.score.breakdown
    orm.status = str(lead.status)
    session.flush()
    return orm


def abrir_run(session: SASession, icp_nome: str, tenant_id: str | None = None) -> RunORM:
    run = RunORM(tenant_id=tenant_id or settings.tenant_id, icp_nome=icp_nome, status="rodando")
    session.add(run)
    session.flush()
    return run


def fechar_run(
    session: SASession, run: RunORM, descobertos: int, novos: int, erros: int, detalhe: str = ""
) -> None:
    run.status = "concluido"
    run.descobertos = descobertos
    run.novos = novos
    run.erros = erros
    run.detalhe = detalhe[:2000] if detalhe else None
    run.terminado_em = datetime.now(UTC)
    session.flush()
