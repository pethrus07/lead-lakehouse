# FARO (lead-lakehouse)

English · [Português](README.pt-BR.md)

A lead capture engine. It looks for businesses across several sources, merges the records that are the same
company, enriches each one with what can be seen from outside (website, e-mail, CNPJ, the Brazilian company
registry number) and scores the opportunity against an ideal customer profile (ICP) that you describe. The
output is a ranked list of leads that can be sent as contacts to a WhatsApp CRM (zapagente).

The repository is called `lead-lakehouse`; FARO is the product name.

## Status

v1 built and tested, not in active use (2026-11). Until 2026-10-31 `main` held v0.6 (Selenium + DuckDB + its own
WhatsApp sender). On 2026-11-01 v1 was merged into `main` and the WhatsApp sender left: this repository only
finds and scores leads. Talking to a lead is another system's job.

## The problem

A small business that sells a service (websites, social media, software) does not know where to start
prospecting. Bought lists are stale, and searching the map one by one takes the whole day. FARO answers "who,
in this region and this niche, needs what I sell the most?", with the reason behind each score.

## How it works

```
SOURCES (several)  ->  DEDUP / identity  ->  ENRICHMENT  ->  ICP SCORE  ->  LEADS
  OpenStreetMap          CNPJ > phone >        website (SSL,     opportunity      -> zapagente
  Google Maps            name + location       e-mail, speed),   weights           (contacts + tags)
  Google Places (paid)                         CNPJ
```

- **Multi-source.** OpenStreetMap (open data, no restrictive terms) and Google Maps (Playwright). Google Places
  only runs with a paid key. CNPJ is enrichment, not discovery: search by business activity code (CNAE) does
  not exist yet.
- **Dedup.** A business found in two sources becomes one record. The key tries CNPJ, then phone, then name plus
  location.
- **ICP score.** The ICP is declarative: niche, region, filters and weights ("no website is worth 5", "no
  WhatsApp is worth -2"). Each score comes with the signals behind it.
- **Sending to the CRM.** `llh enviar-zapagente` creates or updates contacts and tags in zapagente. It does not
  send messages.

## Stack

Python 3.12 with uv, Pydantic v2, SQLAlchemy 2 + Postgres 16 (Docker), httpx, Typer (`llh` CLI), Playwright
(optional, for Google Maps), Streamlit (optional, UI), pytest and ruff.

## Running locally

Requirements: uv and Docker.

```bash
uv sync                          # creates .venv with Python 3.12
cp .env.example .env
docker compose up -d             # Postgres on :5433
uv run llh init-db
uv run llh fontes                # lists the available sources
uv run llh exemplo-icp           # writes a sample ICP to icp_exemplo.json
uv run llh prospectar --help
```

For Google Maps and the UI: `uv sync --extra scraping --extra ui` and `uv run playwright install chromium`.

## Tests

```bash
uv run pytest        # 33 tests, under 1 s, no network and no database
```

## Layout

```
leadlakehouse/
  domain/        pure: models, ICP, scoring, identity, source interface
  sources/       concrete sources (OpenStreetMap, Google Maps, Google Places) and their registry
  enrichment/    website visit and CNPJ
  pipeline/      bronze layer (silver and gold are Postgres tables)
  infra/         database (Postgres/SQLAlchemy) and browser
  integrations/  zapagente client
  app/           use cases (prospecting, sending)
  interface/     `llh` CLI and Streamlit
tests/           pytest
docs/            ARQUITETURA.md, PLANO.md, arquitetura/ (diagrams)
```

Kept out of git: `.env`, `data/` (raw collection), `dados-recebidos/` (received lists with people's contacts).

## Architecture

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) (Portuguese): how everything works, file by file, and in section 17
  what the plan promises and the code does not have.
- [docs/PLANO.md](docs/PLANO.md) (Portuguese): the original phased plan.
- [docs/arquitetura/](docs/arquitetura/README.md): use cases (UML), process (BPMN) and containers (C4).

## Decisions and known limits

- Zero cost by default: no paid source or proxy is on without a key.
- WhatsApp sending does not live here. v0.6 drove WhatsApp Web through Selenium; that was retired (fragile and
  a ban risk).
- Not built yet: discovery by CNPJ/CNAE, Instagram, PageSpeed, WhatsApp number check, Alembic migrations.
- Google Maps selectors break when Google changes the page. They are isolated in one place.
- Collected data never goes into git (Brazil's LGPD privacy law). Open data is the preferred base.

## License

MIT. See [LICENSE](LICENSE).
