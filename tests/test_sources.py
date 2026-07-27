from leadlakehouse.domain.icp import ICP, Regiao
from leadlakehouse.domain.models import Fonte
from leadlakehouse.sources.google_maps import raw_para_business
from leadlakehouse.sources.openstreetmap import (
    elemento_para_business,
    montar_query,
    tags_para_nicho,
)


def test_raw_para_business_maps_maps():
    raw = {
        "nome": "Salão X", "categoria": "Salão de beleza", "telefone": "83999990000",
        "site": None, "nota": 4.5, "n_avaliacoes": 12,
        "links": ["http://instagram.com/salaox", "http://algumsite.com"],
        "url": "https://www.google.com/maps/place/xyz",
    }
    b = raw_para_business(raw)
    assert b.nome == "Salão X"
    assert b.tem_site is False
    assert b.redes_sociais == {"instagram": "http://instagram.com/salaox"}
    assert Fonte.GOOGLE_MAPS in b.fontes
    assert "links" not in b.raw["google_maps"]        # lista grande não é guardada


def test_tags_para_nicho():
    assert ("shop", "hairdresser") in tags_para_nicho("salão de beleza")
    assert tags_para_nicho("padaria") == [("shop", "bakery")]
    assert tags_para_nicho("coisa que nao existe") == []


def test_montar_query_por_municipio():
    icp = ICP(nome="t", nicho=["salão"], regiao=Regiao(municipio="João Pessoa", uf="PB"))
    q = montar_query(icp, "salão")
    assert 'area["name"="João Pessoa"]' in q
    assert 'node(area.a)["shop"="hairdresser"]' in q


def test_montar_query_por_raio():
    icp = ICP(nome="t", nicho=["salão"], regiao=Regiao(lat=-7.1, lng=-34.8, raio_km=3))
    q = montar_query(icp, "salão")
    assert "around:3000,-7.1,-34.8" in q


def test_elemento_para_business_osm():
    icp = ICP(nome="t", regiao=Regiao(municipio="João Pessoa", uf="PB"))
    el = {
        "type": "node", "id": 42, "lat": -7.11, "lon": -34.85,
        "tags": {
            "name": "Barbearia Z", "shop": "hairdresser",
            "phone": "+55 83 99999-0000", "website": "http://z.com.br",
            "addr:city": "João Pessoa",
        },
    }
    b = elemento_para_business(el, icp)
    assert b.nome == "Barbearia Z"
    assert b.tem_site is True
    assert b.categoria == "hairdresser"
    assert b.lat == -7.11 and b.lng == -34.85
    assert b.municipio == "João Pessoa"
    assert Fonte.OPENSTREETMAP in b.fontes


def test_elemento_sem_nome_ignora():
    icp = ICP(nome="t")
    assert elemento_para_business({"type": "node", "id": 1, "tags": {}}, icp) is None
