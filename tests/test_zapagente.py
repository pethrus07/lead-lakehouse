import json

# Asserções com JSON/URLs inline ficam naturalmente longas.
# ruff: noqa: E501
import httpx

from leadlakehouse.integrations.zapagente.client import ZapagenteClient


def _fake_zapagente():
    """Handler que imita a API do zapagente e registra o que recebeu."""
    recebido = {"contatos": [], "tags": [], "aplicacoes": [], "login": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content) if request.content else {}

        if path == "/auth/login":
            recebido["login"] += 1
            assert body["email"] and body["senha"]
            return httpx.Response(200, json={"token": "jwt-xyz", "usuario": {"papel": "admin_tenant"}})

        if path == "/contatos" and request.method == "POST":
            assert request.headers.get("authorization") == "Bearer jwt-xyz"
            assert body["telefone"].isdigit() and len(body["telefone"]) >= 8  # só dígitos
            recebido["contatos"].append(body)
            return httpx.Response(201, json={"id": f"c-{body['telefone']}", "telefone": body["telefone"]})

        if path == "/tags" and request.method == "POST":
            recebido["tags"].append(body["nome"])
            return httpx.Response(201, json={"id": f"t-{body['nome']}", "nome": body["nome"]})

        if path.startswith("/contatos/") and path.endswith("/tags"):
            recebido["aplicacoes"].append((path.split("/")[2], body["tagId"]))
            return httpx.Response(200, json={"ok": True})

        return httpx.Response(404, json={"erro": "nao_encontrado"})

    return handler, recebido


async def test_login_seta_token():
    handler, rec = _fake_zapagente()
    async with ZapagenteClient("http://z", transport=httpx.MockTransport(handler)) as c:
        token = await c.login("demo@zapagente.local", "demo123")
        assert token == "jwt-xyz"
        assert rec["login"] == 1


async def test_enviar_um_upsert_contato_e_tags():
    handler, rec = _fake_zapagente()
    async with ZapagenteClient("http://z", token="jwt-xyz", transport=httpx.MockTransport(handler)) as c:
        contato_id = await c.enviar_um(
            "Salão X", "+55 (83) 99999-0000", ["sem-site", "cidade-joao-pessoa"]
        )
    assert contato_id == "c-5583999990000"                 # telefone virou só dígitos
    assert rec["contatos"][0]["nome"] == "Salão X"
    assert set(rec["tags"]) == {"sem-site", "cidade-joao-pessoa"}
    assert len(rec["aplicacoes"]) == 2                       # duas tags aplicadas ao contato


async def test_tag_cache_nao_recria():
    handler, rec = _fake_zapagente()
    async with ZapagenteClient("http://z", token="jwt-xyz", transport=httpx.MockTransport(handler)) as c:
        await c.enviar_um("A", "5583999990001", ["sem-site"])
        await c.enviar_um("B", "5583999990002", ["sem-site"])   # mesma tag
    assert rec["tags"].count("sem-site") == 1                   # criou a tag uma vez só
    assert len(rec["contatos"]) == 2
