"""ICP (Ideal Customer Profile) — a spec declarativa de critérios de prospecção.

É isto que se edita para "mudar os critérios" sem tocar em código.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .models import Business, Fonte, TipoSinal


class Regiao(BaseModel):
    municipio: str | None = None
    uf: str | None = None
    raio_km: float | None = None
    lat: float | None = None
    lng: float | None = None


class Filtros(BaseModel):
    """Gates duros do ICP. `None` = tanto faz.

    Convenção: para filtros numéricos, quando o negócio não tem o dado (None),
    ele PASSA no filtro — não descartamos por falta de informação; a pontuação
    e a ordenação cuidam do ranking depois.
    """

    tem_site: bool | None = None
    tem_instagram: bool | None = None
    tem_whatsapp: bool | None = None
    nota_min: float | None = None
    nota_max: float | None = None
    min_avaliacoes: int | None = None
    max_avaliacoes: int | None = None
    aberto_apos: date | None = None
    cnae: list[str] | None = None            # prefixos de CNAE aceitos
    situacao_cnpj: list[str] | None = None   # ex.: ["ATIVA"]

    def aprova(self, b: Business) -> bool:
        if self.tem_site is not None and b.tem_site != self.tem_site:
            return False

        if self.tem_instagram is not None:
            tem_insta = "instagram" in b.redes_sociais
            if tem_insta != self.tem_instagram:
                return False

        if self.tem_whatsapp is not None:
            # só descarta se soubermos com certeza que difere
            if b.tem_whatsapp is not None and b.tem_whatsapp != self.tem_whatsapp:
                return False

        if self.nota_min is not None and b.nota is not None and b.nota < self.nota_min:
            return False
        if self.nota_max is not None and b.nota is not None and b.nota > self.nota_max:
            return False

        if self.min_avaliacoes is not None and b.n_avaliacoes is not None \
                and b.n_avaliacoes < self.min_avaliacoes:
            return False
        if self.max_avaliacoes is not None and b.n_avaliacoes is not None \
                and b.n_avaliacoes > self.max_avaliacoes:
            return False

        if self.aberto_apos is not None and b.data_abertura is not None \
                and b.data_abertura < self.aberto_apos:
            return False

        if self.cnae and b.cnae is not None:
            cnae_limpo = b.cnae.replace("-", "").replace("/", "").replace(".", "")
            if not any(cnae_limpo.startswith(p.replace("-", "").replace("/", "").replace(".", ""))
                       for p in self.cnae):
                return False

        if self.situacao_cnpj and b.situacao_cnpj is not None:
            if b.situacao_cnpj.upper() not in {s.upper() for s in self.situacao_cnpj}:
                return False

        return True


# Pesos padrão — enviesados para "vender site/presença digital".
# Ajuste por campanha: vendendo social media, suba INSTA_INATIVO; etc.
PESOS_PADRAO: dict[TipoSinal, float] = {
    TipoSinal.SEM_SITE: 5.0,
    TipoSinal.SO_REDES: 3.0,
    TipoSinal.SITE_SEM_SSL: 3.0,
    TipoSinal.SITE_NAO_RESPONSIVO: 3.0,
    TipoSinal.SITE_LENTO: 2.0,
    TipoSinal.INSTA_INATIVO: 2.0,
    TipoSinal.NEGOCIO_NOVO: 2.0,
    TipoSinal.POUCAS_AVALIACOES: 1.0,
    TipoSinal.NOTA_BAIXA: 1.0,
    TipoSinal.TEM_WHATSAPP: 1.0,    # dá pra alcançar via zapagente
    TipoSinal.SEM_WHATSAPP: -2.0,   # não dá pra alcançar via WhatsApp
}


class PesosOportunidade(BaseModel):
    pesos: dict[TipoSinal, float] = Field(default_factory=lambda: dict(PESOS_PADRAO))
    limiar_alta: float = 5.0
    limiar_media: float = 3.0
    limiar_baixa: float = 0.5

    def peso(self, tipo: TipoSinal) -> float:
        return self.pesos.get(tipo, 0.0)


class ICP(BaseModel):
    """Perfil de cliente ideal — descreve QUEM caçar e o QUE vale mais."""

    nome: str
    nicho: list[str] = Field(default_factory=list)     # termos de busca ou CNAEs
    regiao: Regiao = Field(default_factory=Regiao)
    fontes: list[Fonte] = Field(default_factory=list)  # vazio = todas aplicáveis
    filtros: Filtros = Field(default_factory=Filtros)
    pesos: PesosOportunidade = Field(default_factory=PesosOportunidade)
    limite: int = 100
