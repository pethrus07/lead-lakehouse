"""Cliente HTTP do zapagente.

API (mapeada do repo pethrus07/zapagente): rotas na raiz (sem prefixo /api).
- POST /auth/login {email, senha} -> {token}           (Bearer, 7 dias)
- POST /contatos {nome?, telefone} -> Contato           (UPSERT por (tenant, telefone))
- POST /tags {nome, cor?} -> Tag                         (idempotente por (tenant, nome))
- POST /contatos/:id/tags {tagId} -> {ok}
- POST /campanhas {nome, numeroId, objetivo, contatos:[...]} (opcional; não filtra por tag)

Telefone no zapagente = SÓ DÍGITOS, >= 8 (ex.: 5583996318081) — sem '+'.
Multi-tenant: o tenant vem no JWT; super-admin pode enviar header x-tenant-id.
"""

from __future__ import annotations

import httpx

from ...domain.identity import so_digitos


class ZapagenteError(RuntimeError):
    pass


class ZapagenteClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        tenant_id: str | None = None,   # só para super-admin (header x-tenant-id)
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,   # injetável p/ testes
    ):
        if not base_url:
            raise ZapagenteError("base_url do zapagente não configurada (LLH_ZAPAGENTE_BASE_URL).")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.tenant_id = tenant_id
        self.timeout = timeout
        self._transport = transport
        self._c: httpx.AsyncClient | None = None
        self._tags_cache: dict[str, str] = {}

    async def __aenter__(self) -> ZapagenteClient:
        self._c = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, transport=self._transport
        )
        self._c.headers["Content-Type"] = "application/json"
        if self.token:
            self._c.headers["Authorization"] = f"Bearer {self.token}"
        if self.tenant_id:
            self._c.headers["x-tenant-id"] = self.tenant_id
        return self

    async def __aexit__(self, *exc) -> None:
        if self._c:
            await self._c.aclose()

    # ── auth ────────────────────────────────────────────────
    async def login(self, email: str, senha: str) -> str:
        r = await self._c.post("/auth/login", json={"email": email, "senha": senha})
        if r.status_code != 200:
            raise ZapagenteError(f"login falhou ({r.status_code}): {r.text[:200]}")
        self.token = r.json()["token"]
        self._c.headers["Authorization"] = f"Bearer {self.token}"
        return self.token

    # ── contatos / tags ─────────────────────────────────────
    async def upsert_contato(self, nome: str | None, telefone: str) -> dict:
        tel = so_digitos(telefone)
        if len(tel) < 8:
            raise ZapagenteError(f"telefone inválido: {telefone!r}")
        r = await self._c.post("/contatos", json={"nome": nome, "telefone": tel})
        if r.status_code not in (200, 201):
            raise ZapagenteError(f"upsert contato falhou ({r.status_code}): {r.text[:200]}")
        return r.json()

    async def garantir_tag(self, nome: str, cor: str | None = None) -> str:
        if nome in self._tags_cache:
            return self._tags_cache[nome]
        r = await self._c.post("/tags", json={"nome": nome, "cor": cor})
        if r.status_code not in (200, 201):
            raise ZapagenteError(f"criar tag falhou ({r.status_code}): {r.text[:200]}")
        tag_id = r.json()["id"]
        self._tags_cache[nome] = tag_id
        return tag_id

    async def aplicar_tag(self, contato_id: str, tag_id: str) -> None:
        r = await self._c.post(f"/contatos/{contato_id}/tags", json={"tagId": tag_id})
        if r.status_code not in (200, 201):
            raise ZapagenteError(f"aplicar tag falhou ({r.status_code}): {r.text[:200]}")

    async def enviar_um(self, nome: str | None, telefone: str, tags: list[str]) -> str:
        """Upsert do contato + aplica todas as tags. Retorna o contato_id do zapagente."""
        contato = await self.upsert_contato(nome, telefone)
        contato_id = contato["id"]
        for tag_nome in tags:
            tag_id = await self.garantir_tag(tag_nome)
            await self.aplicar_tag(contato_id, tag_id)
        return contato_id
