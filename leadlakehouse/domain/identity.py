"""Resolução de identidade e dedup entre fontes.

Chave em cascata: CNPJ > telefone(E.164) > nome_normalizado + bucket geográfico.
"""

from __future__ import annotations

import re
import unicodedata

from .models import Business, Fonte


def normalizar_nome(nome: str | None) -> str | None:
    if not nome:
        return None
    txt = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    txt = txt.lower()
    txt = re.sub(r"[^a-z0-9 ]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt or None


def so_digitos(txt: str | None) -> str:
    return re.sub(r"\D", "", txt or "")


def normalizar_telefone(raw: str | None, ddi: str = "55") -> str | None:
    """Normaliza para E.164 brasileiro (+55DD........). Retorna None se implausível."""
    d = so_digitos(raw)
    if not d:
        return None
    if d.startswith("00"):          # DDI internacional discado
        d = d[2:]
    if d.startswith(ddi) and len(d) in (12, 13):   # já tem 55 + DDD + número
        return "+" + d
    if len(d) == 12 and d.startswith("0"):          # tronco antigo: 0 + DDD + número
        d = d[1:]
    if len(d) in (10, 11):          # DDD + número, sem DDI
        return "+" + ddi + d
    if len(d) >= 12:                # provavelmente já internacional
        return "+" + d
    return None


def bucket_geo(lat: float | None, lng: float | None, precisao: int = 3) -> str | None:
    """Bucket geográfico simples (arredonda coords). 3 casas ~ 111 m."""
    if lat is None or lng is None:
        return None
    return f"{round(lat, precisao)},{round(lng, precisao)}"


def chaves_bloqueio(b: Business) -> set[str]:
    """TODAS as chaves fortes do negócio (p/ blocking multi-chave no dedup).

    Dois negócios que compartilhem QUALQUER uma destas são o mesmo mundo real.
    """
    ks: set[str] = set()
    cnpj = so_digitos(b.cnpj)
    if len(cnpj) == 14:
        ks.add(f"cnpj:{cnpj}")
    tel = b.telefone_e164 or normalizar_telefone(b.telefone)
    if tel:
        ks.add(f"tel:{tel}")
    nome = b.nome_norm or normalizar_nome(b.nome)
    geo = bucket_geo(b.lat, b.lng)
    if nome and geo:
        ks.add(f"nomegeo:{nome}|{geo}")
    return ks


def chave_identidade(b: Business) -> str:
    """Chave canônica única (por prioridade) — usada para persistir/upsert."""
    cnpj = so_digitos(b.cnpj)
    if len(cnpj) == 14:
        return f"cnpj:{cnpj}"

    tel = b.telefone_e164 or normalizar_telefone(b.telefone)
    if tel:
        return f"tel:{tel}"

    nome = b.nome_norm or normalizar_nome(b.nome)
    geo = bucket_geo(b.lat, b.lng)
    if nome and geo:
        return f"nomegeo:{nome}|{geo}"
    if nome:
        return f"nome:{nome}"

    # Último recurso: hash do payload cru p/ não colidir tudo em uma chave.
    # ATENÇÃO: hash() de string é aleatorizado por processo, então esta chave NÃO é estável
    # entre execuções — o mesmo negócio pode virar duas linhas. Ver docs/ARQUITETURA.md, seção 18.
    return f"anon:{hash(repr(sorted(b.raw.items()))) & 0xFFFFFFFF:08x}"


def _vazio(v: object) -> bool:
    return v is None or v == "" or (isinstance(v, (list, dict, set)) and len(v) == 0)


def mesclar(a: Business, b: Business) -> Business:
    """Mescla dois negócios (mesmo mundo real). `a` tem prioridade nos escalares."""
    dados = a.model_dump()
    for campo, valor_b in b.model_dump().items():
        if _vazio(dados.get(campo)) and not _vazio(valor_b):
            dados[campo] = valor_b

    m = Business(**dados)

    # Booleanos: presença vence (união de "tem")
    m.tem_site = a.tem_site or b.tem_site
    if a.tem_whatsapp is None:
        m.tem_whatsapp = b.tem_whatsapp
    else:
        m.tem_whatsapp = a.tem_whatsapp or (b.tem_whatsapp or False)

    # Coleções: união
    m.fontes = set(a.fontes) | set(b.fontes)
    m.redes_sociais = {**b.redes_sociais, **a.redes_sociais}
    m.url_origem = {**b.url_origem, **a.url_origem}
    m.raw = {**b.raw, **a.raw}
    m.sinais = list({s.tipo: s for s in (b.sinais + a.sinais)}.values())

    if not m.nome_norm:
        m.nome_norm = normalizar_nome(m.nome)
    if not m.telefone_e164:
        m.telefone_e164 = normalizar_telefone(m.telefone)
    return m


def deduplicar(negocios: list[Business]) -> list[Business]:
    """Colapsa negócios do mesmo mundo real via blocking multi-chave.

    Funde grupos que compartilhem QUALQUER chave forte (CNPJ, telefone, nome+geo) —
    resolve o caso de um registro só-telefone + outro com CNPJ e o mesmo telefone.
    """
    grupos: list[list] = []  # cada item: [chaves: set[str], negocio: Business]
    for b in negocios:
        if not b.nome_norm:
            b.nome_norm = normalizar_nome(b.nome)
        if not b.telefone_e164:
            b.telefone_e164 = normalizar_telefone(b.telefone)

        ks = chaves_bloqueio(b) or {chave_identidade(b)}
        atingidos = [g for g in grupos if g[0] & ks]

        if not atingidos:
            grupos.append([set(ks), b])
            continue

        principal = atingidos[0]
        principal[0] |= ks
        principal[1] = mesclar(principal[1], b)
        for g in atingidos[1:]:          # b uniu grupos antes separados
            principal[0] |= g[0]
            principal[1] = mesclar(principal[1], g[1])
            grupos.remove(g)

    return [g[1] for g in grupos]


__all__ = [
    "Fonte",
    "normalizar_nome",
    "normalizar_telefone",
    "bucket_geo",
    "chave_identidade",
    "mesclar",
    "deduplicar",
]
