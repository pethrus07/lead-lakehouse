from datetime import date

from leadlakehouse.domain.icp import ICP, PesosOportunidade
from leadlakehouse.domain.models import (
    Business,
    Fonte,
    NivelOportunidade,
    Sinal,
    TipoSinal,
)
from leadlakehouse.domain.scoring import derivar_sinais, pontuar

REF = date(2026, 7, 25)


def test_derivar_sinais_sem_site_com_redes():
    b = Business(nome="A", tem_site=False, redes_sociais={"instagram": "x"})
    tipos = {s.tipo for s in derivar_sinais(b, ref=REF)}
    assert TipoSinal.SEM_SITE in tipos
    assert TipoSinal.SO_REDES in tipos


def test_derivar_negocio_novo_e_poucas_avaliacoes():
    b = Business(nome="A", tem_site=True, data_abertura=date(2025, 3, 1), n_avaliacoes=4)
    tipos = {s.tipo for s in derivar_sinais(b, ref=REF)}
    assert TipoSinal.NEGOCIO_NOVO in tipos
    assert TipoSinal.POUCAS_AVALIACOES in tipos
    assert TipoSinal.SEM_SITE not in tipos


def test_negocio_antigo_nao_e_novo():
    b = Business(nome="A", tem_site=True, data_abertura=date(2010, 1, 1))
    tipos = {s.tipo for s in derivar_sinais(b, ref=REF)}
    assert TipoSinal.NEGOCIO_NOVO not in tipos


def test_pontuar_alvo_principal_sem_presenca():
    icp = ICP(nome="sites")
    b = Business(nome="Alvo", tem_site=False, tem_whatsapp=True)
    score = pontuar(b, icp, ref=REF)
    # SEM_SITE (5) + TEM_WHATSAPP (1) = 6 → ALTA
    assert score.valor == 6.0
    assert score.nivel == NivelOportunidade.ALTA
    assert "sem_site" in score.breakdown


def test_pontuar_tem_tudo_nenhuma_oportunidade():
    icp = ICP(nome="sites")
    b = Business(nome="Completo", tem_site=True, nota=4.8, n_avaliacoes=500)
    score = pontuar(b, icp, ref=REF)
    assert score.nivel == NivelOportunidade.NENHUMA
    assert score.valor <= 0


def test_pesos_customizados_mudam_o_ranking():
    # vendendo social media: INSTA_INATIVO passa a valer muito
    pesos = PesosOportunidade(pesos={TipoSinal.INSTA_INATIVO: 8.0, TipoSinal.SEM_SITE: 0.0})
    icp = ICP(nome="social", pesos=pesos)
    b = Business(nome="X", tem_site=False, sinais=[Sinal(tipo=TipoSinal.INSTA_INATIVO,
                                                         fonte=Fonte.INSTAGRAM)])
    score = pontuar(b, icp, ref=REF)
    assert score.breakdown.get("insta_inativo") == 8.0
    assert score.breakdown.get("sem_site") == 0.0
    assert score.nivel == NivelOportunidade.ALTA


def test_sinais_coletados_tem_prioridade_sobre_derivados():
    icp = ICP(nome="sites")
    # negócio tem site, mas enriquecimento detectou site sem SSL
    b = Business(nome="X", tem_site=True,
                 sinais=[Sinal(tipo=TipoSinal.SITE_SEM_SSL, fonte=Fonte.SITE)])
    score = pontuar(b, icp, ref=REF)
    assert "site_sem_ssl" in score.breakdown
