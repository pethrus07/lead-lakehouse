"""Consultas de leitura (para a UI e relatórios). Read-only."""

from __future__ import annotations

from sqlalchemy import text

from ...config import settings
from .base import engine


def leads_df(tenant_id: str | None = None):
    """DataFrame de leads (join com businesses). Import de pandas é tardio (extra 'ui')."""
    import pandas as pd

    tid = tenant_id or settings.tenant_id
    sql = text(
        """
        SELECT l.id, b.nome, l.nivel, l.score, b.telefone_e164, b.email,
               b.tem_site, b.municipio, b.categoria, l.icp_nome, l.status,
               l.tags, l.zapagente_contato_id, b.site
        FROM leads l JOIN businesses b ON b.id = l.business_id
        WHERE l.tenant_id = :tid
        ORDER BY l.score DESC
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params={"tid": tid})


def contagens(tenant_id: str | None = None) -> dict:
    tid = tenant_id or settings.tenant_id
    with engine.connect() as conn:
        neg = conn.execute(
            text("SELECT count(*) FROM businesses WHERE tenant_id=:t"), {"t": tid}
        ).scalar_one()
        leads = conn.execute(
            text("SELECT count(*) FROM leads WHERE tenant_id=:t"), {"t": tid}
        ).scalar_one()
        enviados = conn.execute(
            text("SELECT count(*) FROM leads WHERE tenant_id=:t AND status='enviado_zapagente'"),
            {"t": tid},
        ).scalar_one()
    return {"negocios": neg, "leads": leads, "enviados": enviados}
