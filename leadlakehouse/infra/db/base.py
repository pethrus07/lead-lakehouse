"""Engine e sessão SQLAlchemy. A URL vem do config (`LLH_DATABASE_URL`)."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ...config import settings


class Base(DeclarativeBase):
    pass


def criar_engine(url: str | None = None, echo: bool = False):
    return create_engine(url or settings.database_url, echo=echo, pool_pre_ping=True)


# O engine nasce na importação do módulo, mas o SQLAlchemy só abre conexão no primeiro uso:
# por isso importar isto sem Postgres de pé não explode. URL malformada, essa sim, estoura aqui.
engine = criar_engine()
Session = sessionmaker(bind=engine, expire_on_commit=False)


def criar_tabelas() -> None:
    """Cria as tabelas (uso em dev; em produção usar Alembic)."""
    from . import models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(engine)
