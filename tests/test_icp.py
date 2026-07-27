from datetime import date

from leadlakehouse.domain.icp import Filtros
from leadlakehouse.domain.models import Business


def test_filtro_tem_site():
    f = Filtros(tem_site=False)
    assert f.aprova(Business(nome="A", tem_site=False)) is True
    assert f.aprova(Business(nome="B", tem_site=True)) is False


def test_filtro_tem_instagram():
    f = Filtros(tem_instagram=True)
    assert f.aprova(Business(nome="A", redes_sociais={"instagram": "x"})) is True
    assert f.aprova(Business(nome="B")) is False


def test_filtro_numerico_desconhecido_passa():
    # negócio sem nota NÃO é descartado por um filtro de nota mínima
    f = Filtros(nota_min=4.0)
    assert f.aprova(Business(nome="A")) is True
    assert f.aprova(Business(nome="B", nota=4.5)) is True
    assert f.aprova(Business(nome="C", nota=3.0)) is False


def test_filtro_avaliacoes_faixa():
    f = Filtros(max_avaliacoes=10)   # negócio novo, poucas avaliações
    assert f.aprova(Business(nome="A", n_avaliacoes=3)) is True
    assert f.aprova(Business(nome="B", n_avaliacoes=200)) is False


def test_filtro_aberto_apos():
    f = Filtros(aberto_apos=date(2023, 1, 1))
    assert f.aprova(Business(nome="A", data_abertura=date(2024, 6, 1))) is True
    assert f.aprova(Business(nome="B", data_abertura=date(2020, 1, 1))) is False
    assert f.aprova(Business(nome="C")) is True   # sem data → passa


def test_filtro_cnae_prefixo():
    f = Filtros(cnae=["9602-5"])   # cabeleireiros/estética
    assert f.aprova(Business(nome="A", cnae="9602-5/01")) is True
    assert f.aprova(Business(nome="B", cnae="4711-3/02")) is False


def test_filtro_situacao_cnpj():
    f = Filtros(situacao_cnpj=["ATIVA"])
    assert f.aprova(Business(nome="A", situacao_cnpj="ativa")) is True
    assert f.aprova(Business(nome="B", situacao_cnpj="BAIXADA")) is False
