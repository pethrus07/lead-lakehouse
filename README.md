# lead-lakehouse

> Motor de prospecção multi-fonte. Descobre negócios que precisam do que você vende, pontua a oportunidade e entrega leads prontos para o **zapagente** conversar e fechar.

Ferramenta de uso pessoal, construída numa arquitetura em camadas (padrão zapagente) reutilizável e pronta para virar multi-tenant. Substitui a versão v0.6 (Selenium + DuckDB + Streamlit com outreach próprio).

📄 **Plano de evolução completo:** [`docs/PLANO.md`](docs/PLANO.md)

## Como funciona

```
FONTES (muitas)  →  DEDUP/identidade  →  ENRIQUECIMENTO  →  SCORE por ICP  →  LEADS
  CNPJ, Maps,          CNPJ > tel >         e-mail, SSL,        pesos de          → zapagente
  OSM, Instagram…      nome+geo             site ruim…         oportunidade      (Contatos+Campanhas)
```

- **Descoberta:** parte de dados abertos legais (CNPJ/Receita, OpenStreetMap) e usa scraping (Google Maps, Instagram…) para sinais.
- **Critérios dinâmicos (ICP):** você descreve quem caçar (nicho, região, filtros) e o que vale mais (pesos de oportunidade). O antigo `score_digital` vira um caso particular disso.
- **Outreach:** não existe mais aqui — os leads vão para o **zapagente** (Evolution API, anti-ban, CRM, campanhas).

## Arquitetura (4 camadas)

```
leadlakehouse/
├── domain/        # PURO: models, icp, scoring, identity, interfaces de fonte
├── sources/       # fontes concretas (registry)         [F1/F2]
├── enrichment/    # visita-site, cnpj, whatsapp          [F3]
├── pipeline/      # bronze → silver → gold               [F1]
├── infra/         # db (Postgres/SQLAlchemy), browser
├── integrations/  # cliente zapagente                    [F4]
├── app/           # casos de uso / orquestração          [F1]
├── interface/     # cli (agora), streamlit (F5)
└── config.py      # pydantic-settings (LLH_*)
```

## Setup

Requisitos: **uv** e **Docker** (para o Postgres).

```bash
# 1. Dependências (cria .venv com Python 3.12)
uv sync

# 2. Configuração
cp .env.example .env

# 3. Banco (Postgres em :5433)
docker compose up -d
uv run llh init-db

# 4. Testes
uv run pytest

# 5. CLI
uv run llh versao
uv run llh fontes
```

## Status

**F0 — Fundação** ✅ (config, domínio tipado, ICP/scoring/identity, infra de banco, CLI, testes).
Próximo: **F1** — primeiro motor de fonte (Google Maps em Playwright) + pipeline bronze→silver→gold.

Veja o roadmap por fases em [`docs/PLANO.md`](docs/PLANO.md#12-roadmap-por-fases).

## Legal / LGPD

Base em **dados abertos** (CNPJ/Receita = legal). Scraping respeita rate/ToS por fonte. Dados coletados **não** são versionados (`.gitignore`). Outreach com opt-out vive no zapagente.
