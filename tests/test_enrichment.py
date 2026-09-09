"""Testa as funções puras do enriquecimento, sem rede.

`analisar_html` e `aplicar_cnpj` foram separadas do I/O exatamente para caberem aqui: o que
sobra nos enriquecedores é só a chamada HTTP, que não se testa de graça.
"""

from datetime import date

from leadlakehouse.domain.models import Business, Fonte, TipoSinal
from leadlakehouse.enrichment.cnpj_enrich import aplicar_cnpj
from leadlakehouse.enrichment.site_visitor import analisar_html


def test_analisar_html_site_ruim():
    html = "<html><head></head><body>contato@empresa.com.br</body></html>"
    sinais, extras = analisar_html(html, sem_ssl=True, elapsed=5.0)
    tipos = {s.tipo for s in sinais}
    assert TipoSinal.SITE_SEM_SSL in tipos
    assert TipoSinal.SITE_NAO_RESPONSIVO in tipos    # sem viewport
    assert TipoSinal.SITE_LENTO in tipos
    assert extras["email"] == "contato@empresa.com.br"


def test_analisar_html_site_bom():
    html = (
        '<html><head><meta name="viewport" content="width=device-width">'
        "</head><body>ok</body></html>"
    )
    sinais, extras = analisar_html(html, sem_ssl=False, elapsed=0.4)
    tipos = {s.tipo for s in sinais}
    assert TipoSinal.SITE_NAO_RESPONSIVO not in tipos
    assert TipoSinal.SITE_SEM_SSL not in tipos
    assert TipoSinal.SITE_LENTO not in tipos
    assert "email" not in extras


def test_analisar_html_detecta_whatsapp():
    html = '<a href="https://wa.me/5583999990000">fale conosco</a>'
    _, extras = analisar_html(html, sem_ssl=False, elapsed=0.2)
    assert extras.get("tem_whatsapp") is True


def test_aplicar_cnpj_preenche_campos():
    b = Business(cnpj="11.111.111/0001-11")
    d = {
        "razao_social": "EMPRESA X LTDA",
        "cnae_fiscal": 9602501,
        "descricao_situacao_cadastral": "ATIVA",
        "data_inicio_atividade": "2024-05-01",
        "municipio": "JOAO PESSOA",
        "uf": "PB",
    }
    b = aplicar_cnpj(b, d)
    assert b.nome == "EMPRESA X LTDA"
    assert b.cnae == "9602501"
    assert b.situacao_cnpj == "ATIVA"
    assert b.data_abertura == date(2024, 5, 1)
    assert b.municipio == "JOAO PESSOA"
    assert Fonte.CNPJ in b.fontes
