"""Camada bronze — persiste o resultado bruto de cada fonte (imutável, rastreável)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from ..config import settings
from ..domain.models import Business, Fonte


def _slug(txt: str, limite: int = 40) -> str:
    limpo = "".join(c if (c.isalnum() or c in " -_") else " " for c in txt)
    return "_".join(limpo.split())[:limite]


def salvar_bronze(negocios: list[Business], fonte: Fonte, query: str = "") -> str | None:
    """Grava os negócios crus de uma fonte em `data/bronze/<fonte>/<ts>_<query>.json`."""
    if not negocios:
        return None
    destino = os.path.join(settings.bronze_dir, str(fonte))
    os.makedirs(destino, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    nome = f"{ts}_{_slug(query)}.json" if query else f"{ts}.json"
    caminho = os.path.join(destino, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(
            [b.model_dump(mode="json") for b in negocios],
            f, ensure_ascii=False, indent=2, default=str,
        )
    return caminho
