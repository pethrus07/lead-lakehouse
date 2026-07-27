"""Tabelas ORM (camadas silver/gold + manifesto de execução).

Toda tabela nasce com `tenant_id` (single-tenant hoje, multi-tenant-ready).
Sinais ficam embutidos em JSON no negócio (uma tabela `signals` dedicada pode
vir depois, se precisarmos consultar por sinal).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _agora() -> datetime:
    return datetime.now(UTC)


class BusinessORM(Base):
    __tablename__ = "businesses"
    __table_args__ = (UniqueConstraint("tenant_id", "chave_identidade", name="uq_business_ident"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    chave_identidade: Mapped[str] = mapped_column(String(255), index=True)

    cnpj: Mapped[str | None] = mapped_column(String(14))
    nome: Mapped[str | None] = mapped_column(String(255))
    nome_norm: Mapped[str | None] = mapped_column(String(255), index=True)

    telefone: Mapped[str | None] = mapped_column(String(40))
    telefone_e164: Mapped[str | None] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    site: Mapped[str | None] = mapped_column(String(500))
    tem_site: Mapped[bool] = mapped_column(Boolean, default=False)
    tem_whatsapp: Mapped[bool | None] = mapped_column(Boolean)
    redes_sociais: Mapped[dict] = mapped_column(JSON, default=dict)

    categoria: Mapped[str | None] = mapped_column(String(255))
    cnae: Mapped[str | None] = mapped_column(String(20), index=True)
    nota: Mapped[float | None] = mapped_column(Float)
    n_avaliacoes: Mapped[int | None] = mapped_column(Integer)
    data_abertura: Mapped[date | None] = mapped_column(Date)
    situacao_cnpj: Mapped[str | None] = mapped_column(String(40))

    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    municipio: Mapped[str | None] = mapped_column(String(120), index=True)
    uf: Mapped[str | None] = mapped_column(String(2))
    endereco: Mapped[str | None] = mapped_column(String(500))

    fontes: Mapped[list] = mapped_column(JSON, default=list)
    sinais: Mapped[list] = mapped_column(JSON, default=list)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    coletado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora, onupdate=_agora
    )

    leads: Mapped[list[LeadORM]] = relationship(back_populates="business")


class IcpORM(Base):
    __tablename__ = "icps"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    nome: Mapped[str] = mapped_column(String(120))
    spec: Mapped[dict] = mapped_column(JSON)   # o ICP serializado
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)


class LeadORM(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    icp_nome: Mapped[str] = mapped_column(String(120), index=True)

    score: Mapped[float] = mapped_column(Float, index=True)
    nivel: Mapped[str] = mapped_column(String(20), index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(30), default="novo", index=True)
    zapagente_contato_id: Mapped[str | None] = mapped_column(String(64))

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    business: Mapped[BusinessORM] = relationship(back_populates="leads")


class RunORM(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    icp_nome: Mapped[str] = mapped_column(String(120))
    fonte: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="rodando")
    descobertos: Mapped[int] = mapped_column(Integer, default=0)
    novos: Mapped[int] = mapped_column(Integer, default=0)
    erros: Mapped[int] = mapped_column(Integer, default=0)
    detalhe: Mapped[str | None] = mapped_column(Text)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    terminado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
