"""Envio de leads ao zapagente: carrega pendentes → upsert contato + tags → marca enviado."""

from __future__ import annotations

import structlog
from sqlalchemy import select

from ..config import settings
from ..domain.identity import so_digitos
from ..infra.db.base import Session
from ..infra.db.models import BusinessORM, LeadORM
from ..integrations.zapagente.client import ZapagenteClient, ZapagenteError

log = structlog.get_logger()


def _pendentes(session, icp_nome: str | None, limite: int | None):
    q = (
        select(LeadORM, BusinessORM)
        .join(BusinessORM, BusinessORM.id == LeadORM.business_id)
        .where(LeadORM.tenant_id == settings.tenant_id, LeadORM.status != "enviado_zapagente")
        .order_by(LeadORM.score.desc())
    )
    if icp_nome:
        q = q.where(LeadORM.icp_nome == icp_nome)
    if limite:
        q = q.limit(limite)
    return session.execute(q).all()


async def enviar_ao_zapagente(
    icp_nome: str | None = None,
    limite: int | None = None,
    email: str | None = None,
    senha: str | None = None,
    dry_run: bool = False,
) -> dict:
    enviados = erros = ignorados = 0

    # dry-run: só conta os pendentes com telefone válido, sem falar com o zapagente.
    if dry_run:
        with Session() as session:
            for _lead, biz in _pendentes(session, icp_nome, limite):
                tel = biz.telefone_e164 or biz.telefone
                if tel and len(so_digitos(tel)) >= 8:
                    enviados += 1
                else:
                    ignorados += 1
        log.info("envio_zapagente", enviados=enviados, ignorados=ignorados, dry_run=True)
        return {"enviados": enviados, "erros": 0, "ignorados": ignorados}

    client = ZapagenteClient(
        base_url=settings.zapagente_base_url,
        token=settings.zapagente_token or None,
    )
    async with client:
        if email and senha and not client.token:
            await client.login(email, senha)
        if not client.token:
            raise ZapagenteError(
                "Sem credenciais: defina LLH_ZAPAGENTE_TOKEN no .env ou passe --email/--senha."
            )

        with Session() as session:
            pares = _pendentes(session, icp_nome, limite)
            for lead_orm, biz in pares:
                tel = biz.telefone_e164 or biz.telefone
                if not tel or len(so_digitos(tel)) < 8:
                    ignorados += 1
                    continue
                try:
                    contato_id = await client.enviar_um(biz.nome, tel, lead_orm.tags or [])
                    lead_orm.status = "enviado_zapagente"
                    lead_orm.zapagente_contato_id = str(contato_id)
                    enviados += 1
                except Exception as e:  # noqa: BLE001
                    erros += 1
                    log.warning("erro_envio", nome=biz.nome, erro=str(e))
            session.commit()

    log.info("envio_zapagente", enviados=enviados, erros=erros, ignorados=ignorados)
    return {"enviados": enviados, "erros": erros, "ignorados": ignorados}
