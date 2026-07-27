"""Entidades do domínio (Pydantic v2). Sem I/O."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Fonte(StrEnum):
    """De onde veio o dado."""

    CNPJ = "cnpj"                    # dados abertos da Receita
    GOOGLE_MAPS = "google_maps"
    GOOGLE_PLACES = "google_places"  # API oficial (paga, opcional)
    OPENSTREETMAP = "openstreetmap"
    INSTAGRAM = "instagram"
    SERP = "serp"                    # busca do Google
    FACEBOOK = "facebook"
    BING = "bing"
    FOURSQUARE = "foursquare"
    DIRETORIO = "diretorio"          # Apontador, GuiaMais, TeleListas...
    MARKETPLACE = "marketplace"      # iFood, MercadoLivre, OLX...
    SITE = "site"                    # enriquecimento pela visita ao site
    MANUAL = "manual"


class TipoSinal(StrEnum):
    """Sinais de oportunidade detectados sobre um negócio."""

    SEM_SITE = "sem_site"
    SO_REDES = "so_redes"
    SITE_SEM_SSL = "site_sem_ssl"
    SITE_NAO_RESPONSIVO = "site_nao_responsivo"
    SITE_LENTO = "site_lento"
    INSTA_INATIVO = "insta_inativo"
    NEGOCIO_NOVO = "negocio_novo"
    POUCAS_AVALIACOES = "poucas_avaliacoes"
    NOTA_BAIXA = "nota_baixa"
    TEM_WHATSAPP = "tem_whatsapp"
    SEM_WHATSAPP = "sem_whatsapp"


class NivelOportunidade(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"
    NENHUMA = "nenhuma"


class LeadStatus(StrEnum):
    NOVO = "novo"
    ENVIADO_ZAPAGENTE = "enviado_zapagente"
    DESCARTADO = "descartado"


class Sinal(BaseModel):
    """Um sinal de oportunidade individual. Deduplicado sempre por `tipo`."""

    tipo: TipoSinal
    fonte: Fonte | None = None
    detalhe: str | None = None
    valor: float | int | str | None = None


class Business(BaseModel):
    """Negócio consolidado (camada silver) — a unidade central do domínio."""

    # Identidade
    cnpj: str | None = None
    nome: str | None = None
    nome_norm: str | None = None

    # Contato
    telefone: str | None = None          # bruto, como veio da fonte
    telefone_e164: str | None = None     # normalizado (+55...)
    email: str | None = None
    site: str | None = None
    tem_site: bool = False
    tem_whatsapp: bool | None = None
    redes_sociais: dict[str, str] = Field(default_factory=dict)  # {"instagram": url}

    # Negócio
    categoria: str | None = None
    cnae: str | None = None
    nota: float | None = None
    n_avaliacoes: int | None = None
    data_abertura: date | None = None
    situacao_cnpj: str | None = None

    # Geo
    lat: float | None = None
    lng: float | None = None
    municipio: str | None = None
    uf: str | None = None
    endereco: str | None = None

    # Proveniência
    fontes: set[Fonte] = Field(default_factory=set)
    url_origem: dict[str, str] = Field(default_factory=dict)   # {fonte_value: url}
    sinais: list[Sinal] = Field(default_factory=list)          # coletados no enriquecimento
    raw: dict = Field(default_factory=dict)                    # payload cru por fonte
    coletado_em: datetime | None = None


class Score(BaseModel):
    """Resultado da pontuação de oportunidade de um negócio para um ICP."""

    valor: float
    nivel: NivelOportunidade
    sinais: list[Sinal] = Field(default_factory=list)
    breakdown: dict[str, float] = Field(default_factory=dict)


class Lead(BaseModel):
    """Negócio pontuado, pronto para virar contato no zapagente (camada gold)."""

    business: Business
    icp_nome: str
    score: Score
    tags: list[str] = Field(default_factory=list)
    status: LeadStatus = LeadStatus.NOVO
