from leadlakehouse.domain.identity import (
    bucket_geo,
    chave_identidade,
    deduplicar,
    mesclar,
    normalizar_nome,
    normalizar_telefone,
)
from leadlakehouse.domain.models import Business, Fonte


def test_normalizar_telefone_variacoes():
    assert normalizar_telefone("(83) 99999-1234") == "+5583999991234"
    assert normalizar_telefone("83999991234") == "+5583999991234"
    assert normalizar_telefone("5583999991234") == "+5583999991234"
    assert normalizar_telefone("83 3241-1234") == "+558332411234"     # fixo, 10 dígitos
    assert normalizar_telefone("083999991234") == "+5583999991234"    # tronco 0 + DDD
    assert normalizar_telefone("") is None
    assert normalizar_telefone("123") is None
    assert normalizar_telefone(None) is None


def test_normalizar_nome():
    assert normalizar_nome("Salão da Márcia & Cia!") == "salao da marcia cia"
    assert normalizar_nome("  AÇAÍ   do  Zé ") == "acai do ze"
    assert normalizar_nome(None) is None
    assert normalizar_nome("") is None


def test_bucket_geo():
    assert bucket_geo(-7.123456, -34.845678) == "-7.123,-34.846"
    assert bucket_geo(None, -34.8) is None


def test_chave_identidade_prioriza_cnpj_depois_tel():
    b_cnpj = Business(cnpj="12.345.678/0001-90", nome="X", telefone="83999991234")
    assert chave_identidade(b_cnpj) == "cnpj:12345678000190"

    b_tel = Business(nome="Y", telefone="(83) 99999-1234")
    assert chave_identidade(b_tel) == "tel:+5583999991234"

    b_nomegeo = Business(nome="Padaria Central", lat=-7.12, lng=-34.84)
    assert chave_identidade(b_nomegeo).startswith("nomegeo:padaria central|")

    b_nome = Business(nome="Padaria Central")
    assert chave_identidade(b_nome) == "nome:padaria central"


def test_mesclar_une_fontes_e_preenche_vazios():
    a = Business(nome="Petshop Bicho", telefone="83999991234", fontes={Fonte.GOOGLE_MAPS},
                 tem_site=False)
    b = Business(nome="Petshop Bicho", email="contato@bicho.com", tem_site=True,
                 fontes={Fonte.CNPJ}, redes_sociais={"instagram": "http://insta/bicho"})
    m = mesclar(a, b)
    assert m.email == "contato@bicho.com"       # preencheu vazio de `a`
    assert m.telefone == "83999991234"          # manteve o de `a`
    assert m.tem_site is True                    # presença vence
    assert m.fontes == {Fonte.GOOGLE_MAPS, Fonte.CNPJ}
    assert m.redes_sociais == {"instagram": "http://insta/bicho"}


def test_deduplicar_colapsa_mesmo_negocio_de_fontes_diferentes():
    do_maps = Business(nome="Auto Center Silva", telefone="(83) 99999-0001",
                       fontes={Fonte.GOOGLE_MAPS}, nota=4.5)
    do_cnpj = Business(nome="AUTO CENTER SILVA LTDA", telefone="8399999-0001",
                       cnpj="11.111.111/0001-11", fontes={Fonte.CNPJ})
    # mesmo telefone → mesma chave (tel), colapsam
    resultado = deduplicar([do_maps, do_cnpj])
    assert len(resultado) == 1
    assert resultado[0].nota == 4.5
    assert resultado[0].cnpj == "11.111.111/0001-11"
    assert resultado[0].fontes == {Fonte.GOOGLE_MAPS, Fonte.CNPJ}
