# lead-lakehouse

> Motor de prospecção multi-fonte. Descobre negócios que precisam do que você vende, pontua a oportunidade e entrega leads prontos para o **zapagente** conversar e fechar.

> **Para entender o código sozinho, comece por [docs/ARQUITETURA.md](docs/ARQUITETURA.md).**

Ferramenta de uso pessoal, construída numa arquitetura em camadas (padrão zapagente) reutilizável e pronta para virar multi-tenant. Substitui a versão v0.6 (Selenium + DuckDB + Streamlit com outreach próprio).

📄 **Plano de evolução completo:** [`docs/PLANO.md`](docs/PLANO.md)

## Como funciona

```
FONTES (muitas)  →  DEDUP/identidade  →  ENRIQUECIMENTO  →  SCORE por ICP  →  LEADS
  OSM, Maps,           CNPJ > tel >         site (SSL, e-mail,  pesos de          → zapagente
  Places (paga)        nome+geo             velocidade), CNPJ   oportunidade      (Contatos + Tags)
```

- **Descoberta:** OpenStreetMap (dado aberto, sem ToS) e Google Maps (Playwright); Google Places entra só se houver chave paga. CNPJ/Receita é **enriquecimento**, não descoberta — a busca por CNAE ainda não foi construída.
- **Critérios dinâmicos (ICP):** você descreve quem caçar (nicho, região, filtros) e o que vale mais (pesos de oportunidade). O antigo `score_digital` vira um caso particular disso.
- **Outreach:** não existe mais aqui — os leads vão para o **zapagente** (Evolution API, anti-ban, CRM, campanhas).

## Arquitetura (4 camadas)

```
leadlakehouse/
├── domain/        # PURO: models, icp, scoring, identity, interfaces de fonte
├── sources/       # fontes concretas (registry)         [F1/F2]
├── enrichment/    # visita-site (SSL/e-mail/velocidade), cnpj
├── pipeline/      # bronze (silver e gold são as tabelas do Postgres)
├── infra/         # db (Postgres/SQLAlchemy), browser
├── integrations/  # cliente zapagente                    [F4]
├── app/           # casos de uso / orquestração          [F1]
├── interface/     # cli (`llh`) e streamlit
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

**F0 a F5 construídas** na branch `refactor/v1-multi-fonte`: domínio tipado (ICP, scoring, identity), fontes OpenStreetMap e Google Maps, enriquecimento de site e de CNPJ, Postgres, CLI de seis comandos, conector zapagente e UI Streamlit. **33 testes passando, ruff limpo.**

**Ainda não existe:** descoberta por CNPJ/CNAE, Instagram e as demais fontes dos Tiers 1 e 2, PageSpeed, verificação de WhatsApp, migrações Alembic e o disparo de campanha no zapagente. A lista completa do que o plano promete e o código não tem está na seção 17 de [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

Roadmap por fases em [`docs/PLANO.md`](docs/PLANO.md#12-roadmap-por-fases).

## Legal / LGPD

Base em **dados abertos** (CNPJ/Receita = legal). Scraping respeita rate/ToS por fonte. Dados coletados **não** são versionados (`.gitignore`). Outreach com opt-out vive no zapagente.
