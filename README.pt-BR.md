# FARO (lead-lakehouse)

[English](README.md) · Português

Motor de captação de clientes. Busca negócios em várias fontes, junta os registros que são a mesma empresa,
enriquece cada um com o que dá para ver de fora (site, e-mail, CNPJ) e dá uma nota de oportunidade conforme um
perfil de cliente ideal (ICP) que você descreve. O resultado é uma lista de leads ordenada, que pode ser
enviada como contatos para um CRM de WhatsApp (o zapagente).

O repositório se chama `lead-lakehouse`; FARO é o nome do produto.

## Status

v1 construída e testada, em pausa de uso (11/2026). Até 31/10/2026 o `main` tinha a v0.6 (Selenium + DuckDB +
disparo de WhatsApp próprio). Em 01/11/2026 a v1 entrou no `main` e o disparo de WhatsApp saiu: este
repositório só acha e pontua leads. Conversar com o lead é papel de outro sistema.

## O problema

Pequeno negócio que vende serviço (site, social media, sistema) não sabe por onde começar a prospectar.
Listas compradas são velhas, e procurar um por um no mapa toma o dia. O FARO responde "quem, nesta região e
neste nicho, mais precisa do que eu vendo?", com o motivo de cada nota.

## O que faz

```
FONTES (várias)  ->  DEDUP / identidade  ->  ENRIQUECIMENTO  ->  NOTA por ICP  ->  LEADS
  OpenStreetMap        CNPJ > telefone >      site (SSL, e-mail,     pesos de            -> zapagente
  Google Maps          nome + local           velocidade), CNPJ      oportunidade         (contatos + tags)
  Google Places (paga)
```

- **Multi-fonte.** OpenStreetMap (dado aberto, sem termos de uso restritivos) e Google Maps (Playwright).
  Google Places só entra com chave paga. CNPJ é enriquecimento, não descoberta: a busca por CNAE não existe.
- **Dedup.** Um negócio que aparece em duas fontes vira um registro só. A chave tenta CNPJ, depois telefone,
  depois nome com localização.
- **Nota por ICP.** O ICP é declarativo: nicho, região, filtros e pesos ("sem site vale 5", "sem WhatsApp vale
  -2"). A nota vem com os sinais que a formaram.
- **Envio para o CRM.** `llh enviar-zapagente` cria ou atualiza os contatos e as tags no zapagente. Não manda
  mensagem.

## Stack

Python 3.12 com uv, Pydantic v2, SQLAlchemy 2 + Postgres 16 (Docker), httpx, Typer (CLI `llh`), Playwright
(opcional, para o Google Maps), Streamlit (opcional, interface), pytest e ruff.

## Rodar localmente

Requisitos: uv e Docker.

```bash
uv sync                          # cria .venv com Python 3.12
cp .env.example .env
docker compose up -d             # Postgres em :5433
uv run llh init-db
uv run llh fontes                # lista as fontes disponíveis
uv run llh exemplo-icp           # gera um ICP de exemplo em icp_exemplo.json
uv run llh prospectar --help
```

Para o Google Maps e a interface: `uv sync --extra scraping --extra ui` e `uv run playwright install chromium`.

## Testes

```bash
uv run pytest        # 33 testes, menos de 1 s, sem rede e sem banco
```

## Pastas

```
leadlakehouse/
  domain/        puro: modelos, ICP, nota, identidade, interface de fonte
  sources/       fontes concretas (OpenStreetMap, Google Maps, Google Places) e o registro delas
  enrichment/    visita ao site e CNPJ
  pipeline/      camada bronze (silver e gold são tabelas do Postgres)
  infra/         banco (Postgres/SQLAlchemy) e navegador
  integrations/  cliente do zapagente
  app/           casos de uso (prospecção, envio)
  interface/     CLI `llh` e Streamlit
tests/           pytest
docs/            ARQUITETURA.md, PLANO.md, arquitetura/ (diagramas)
```

Fora do git: `.env`, `data/` (coleta bruta), `dados-recebidos/` (listas recebidas com contato de pessoas).

## Arquitetura

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): o funcionamento inteiro, arquivo por arquivo, e na seção 17 o que
  o plano promete e o código não tem.
- [docs/PLANO.md](docs/PLANO.md): o plano original por fases.
- [docs/arquitetura/](docs/arquitetura/README.md): casos de uso (UML), processo (BPMN) e containers (C4).

## Decisões e limites conhecidos

- Custo zero por padrão: nenhuma fonte ou proxy pago fica ligado sem chave.
- Disparo de WhatsApp não mora aqui. A v0.6 automatizava o WhatsApp Web por Selenium; isso foi aposentado
  (frágil e com risco de banimento).
- Ainda não existem: descoberta por CNPJ/CNAE, Instagram, PageSpeed, verificação de WhatsApp, migrações
  Alembic.
- Os seletores do Google Maps quebram quando o Google muda a página. Ficam isolados num ponto só.
- Dados coletados nunca entram no git (LGPD). Base preferida: dados abertos.

## Licença

MIT. Veja [LICENSE](LICENSE).
