# FARO — Plano de Evolução (v1)

> Motor de prospecção multi-fonte. Acha negócios que precisam do que você vende, pontua a oportunidade e entrega leads prontos pro **zapagente** conversar e fechar.
>
> Documento de planejamento. Autor: Pedro Oliveira. Data: 2026-07-25.

---

## ✅ Estado da implementação (2026-07-25)

**F0 → F5 CONSTRUÍDAS** na branch `refactor/v1-multi-fonte` (produto = `lead-lakehouse`; FARO era a adaptação Supernova). 33 testes verdes, ruff limpo, validado ao vivo (OpenStreetMap → Postgres).

| Fase | Status | Entregue |
|---|---|---|
| F0 Fundação | ✅ | pacote `leadlakehouse/` 4 camadas, config, domínio tipado (ICP/scoring/identity), Postgres/SQLAlchemy, CLI |
| F1 Motor 1 fonte | ✅ | Google Maps (Playwright) + pipeline bronze→silver→gold + orquestrador + repository |
| F2 Multi-fonte | ✅ | **OpenStreetMap/Overpass** (live, mirrors, zero custo) + CNPJ enrich; registro de fontes; dedup multi-chave |
| F3 Enriquecimento | ✅ | visita-site (SSL/responsivo/velocidade/e-mail/whatsapp) + CNPJ (minhareceita) + score por ICP |
| F4 Conector zapagente | ✅ | `ZapagenteClient` (auth/upsert contatos/tags) + `llh enviar-zapagente`; **outreach Selenium REMOVIDO** |
| F5 UI | ✅ | Streamlit (editor de ICP, rodar prospecção, leads, enviar) |
| F6 SaaS | ⬜ futuro | FastAPI + fila + multi-tenant real |

**Pendências conhecidas:** (1) descoberta CNPJ-por-CNAE precisa da base aberta da Receita (dataset/token) — hoje CNPJ é só enriquecimento; (2) selectores do Google Maps são frágeis por natureza (isolados e testáveis no mapeamento); (3) Docker Desktop instável nesta máquina derruba o Postgres (reiniciar o container quando cair).

---

## 0. Decisões já travadas

| # | Decisão | Escolha |
|---|---|---|
| 1 | Formato do produto | **Ferramenta pessoal agora**, mas stack reutilizável e arquitetura top-level (padrão zapagente), pronta pra virar multi-tenant. |
| 2 | Outreach WhatsApp | **Aposentar o Selenium** (`outreach/whatsapp_sender.py`). Leads passam a entrar no **zapagente** (Evolution API, anti-ban, CRM, campanhas). |
| 3 | Motor de scraping | **Multi-fonte** — o máximo de fontes disponíveis. Recomendação minha na §4. |
| 4 | Primeiro passo | **Este plano.** |

---

## 1. Visão do produto

Hoje o `lead-lakehouse` faz tudo num lugar só: acha lead **e** dispara WhatsApp. A partir de agora, dois motores separados e complementares:

```
┌──────────────────────────┐        ┌──────────────────────────┐
│  FARO  (motor de          │  leads │  zapagente (motor de      │
│  PROSPECÇÃO / topo funil) │ ─────► │  CONVERSÃO / fundo funil) │
│                           │  tags  │                           │
│  multi-fonte → dedup →    │        │  Contatos + Campanhas +   │
│  enriquece → pontua ICP   │        │  Missões IA (WhatsApp)    │
└──────────────────────────┘        └──────────────────────────┘
         "quem precisa"                    "aborda e fecha"
```

**FARO encontra e qualifica. zapagente aborda e fecha.** Juntos = máquina de aquisição fim-a-fim.

O outreach por Selenium (frágil, alto risco de ban) morre. Quem faz WhatsApp de verdade é o zapagente, que já tem Evolution API, anti-ban, tiers, tags e campanhas.

---

## 2. Princípios de arquitetura

Espelhar a **disciplina** do zapagente (monólito em camadas, tipado, testável), mas em Python — porque o ecossistema de scraping (Playwright, parsing, anti-detecção) é imbatível em Python.

**4 camadas, dependência sempre pra dentro:**

```
┌─ Interface ──────────────────────────────────────────┐
│  CLI  ·  Streamlit (agora)  ·  FastAPI (depois)       │
├─ Aplicação / Casos de uso ───────────────────────────┤
│  "rodar prospecção de um ICP"  ·  "enviar p/ zapagente"│
├─ Domínio (puro, sem I/O) ────────────────────────────┤
│  Business · Lead · ICP · Signal · Score · interfaces  │
│  de Source  ·  regras de pontuação  ·  dedup           │
├─ Infra ──────────────────────────────────────────────┤
│  Sources (Maps, CNPJ, Insta…) · Repos (Postgres) ·    │
│  BrowserPool · cliente zapagente · cache               │
└──────────────────────────────────────────────────────┘
```

Regras:
- **Single-tenant agora, multi-tenant-ready.** Toda tabela nasce com `tenant_id` (default = seu tenant). Repositórios abstraídos — trocar/particionar depois é barato.
- **Domínio não sabe de Selenium, HTTP nem SQL.** Fontes e repositórios são interfaces; implementações ficam na infra. Isso é o que deixa a stack reutilizável.
- **Tudo tipado** com Pydantic v2 (equivalente ao Prisma/TS do zapagente).
- **Config por `.env`** (pydantic-settings). Zero segredo no código.

---

## 3. Stack recomendada

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | **Python 3.12** | Ecossistema de scraping/anti-detecção. (Você já tem 3.14 pro whisper; fixamos 3.12 estável num venv próprio do projeto.) |
| Browser | **Playwright (async)** | Mais rápido, headless de verdade, concorrência nativa, mais furtivo e estável que Selenium. Substitui o Selenium atual. |
| HTTP/APIs | **httpx (async)** | Fontes que são API (CNPJ, Overpass, Places) não precisam de browser. |
| Parsing | **selectolax** (+ BeautifulSoup fallback) | Rápido pra extrair sinais de sites. |
| Modelos/Config | **Pydantic v2 + pydantic-settings** | Tipagem do domínio e da spec de ICP. |
| Banco operacional | **PostgreSQL** (Docker) + **SQLAlchemy 2.0 + Alembic** | Igual ao zapagente, pronto p/ multi-tenant. Você já roda Postgres/Docker/WSL2. *(DuckDB fica como opção analítica na camada bronze — ver §6.)* |
| Concorrência | **asyncio** (agora) → **Arq/Redis** (fila, quando virar SaaS) | Escala sem reescrever. |
| Logs | **structlog** | Logs estruturados + manifesto por execução. |
| Testes | **pytest** + fixtures de HTML | Contrato de cada fonte + parsers testados contra HTML salvo (pega quebra do Google cedo). |
| UI | **Streamlit** (reaproveita a atual, bonita) | Depois FastAPI + painel. |

> **Decisão aberta A (não bloqueante):** Postgres desde já (recomendo, por causa do "multi-tenant-ready") **vs.** continuar no DuckDB e abstrair o repositório pra migrar depois. Recomendo Postgres. Me diga se prefere adiar.

---

## 4. Fontes de dados — o "scraper absurdo" 🔥

O pulo do gato: **inverter o modelo**. Hoje você raspa o Google Maps *pra achar* negócios (frágil, limitado, contra ToS). O certo é começar de **dados abertos legais e estruturados** e usar scraping só pra adicionar **sinais de oportunidade**.

Toda fonte implementa uma de duas interfaces → adicionar fonte nova = escrever um arquivo e registrar:

- `DiscoverySource` — dado um ICP (nicho + região + filtros), **descobre** negócios.
- `EnrichmentSource` — dado um negócio, **adiciona sinais** (e-mail, site, redes, CNPJ…).

### Tier 0 — Base legal e estruturada (a fundação, sem ToS)
| Fonte | Tipo | O que entrega | Por que é ouro |
|---|---|---|---|
| **CNPJ / Receita Federal** (dados abertos: minhareceita, Brasil.io, CNPJ.ws) | Discovery + Enrich | **TODA** empresa por **CNAE** (atividade) + município: razão social, endereço, situação, **data de abertura**, sócios, capital | Legal, massivo, estruturado. "Todas as farmácias de Bayeux" numa query. **É a base do produto.** |
| **OpenStreetMap / Overpass API** | Discovery | POIs por categoria + área geográfica (bbox/raio) | Livre, sem ToS, ótimo pra geolocalizar e cruzar. |

### Tier 1 — Descoberta rica (coração do produto)
| Fonte | Tipo | O que entrega | Nota |
|---|---|---|---|
| **Google Maps** (Playwright robusto) | Discovery + Enrich | nome, categoria, telefone, site, nota, nº avaliações, horários | Parsers isolados e testados; é o que quebra mais, então fica encapsulado. |
| **Google Places API** (oficial, pago) | Discovery + Enrich | os mesmos dados, estável, legal | **Híbrido:** usa a API pros dados-base e scraping só pros sinais que a API não dá. Custo por request. |
| **Instagram** (perfis business por local/hashtag) | Discovery + Enrich | presença social, atividade, link da bio, seguidores | Muito forte no BR. ToS sensível → rate baixo, cuidado. |
| **Google Search / SERP** | Enrich | tem site? ranqueia? | Sinal de maturidade digital. |

### Tier 2 — Complementares (cauda longa / cross-check)
| Fonte | Tipo | Uso |
|---|---|---|
| **Facebook Pages** | Discovery/Enrich | negócios locais sem Maps |
| **Bing Places / Foursquare** | Discovery | alternativa + cruzar/validar |
| **Diretórios BR** (Apontador, GuiaMais, TeleListas) | Discovery | cauda longa |
| **Marketplaces** (iFood, MercadoLivre, OLX) | Discovery | restaurantes / vendedores por nicho |

### Enriquecimento (sinais sobre um negócio já achado)
| Enriquecedor | Sinal de oportunidade que gera |
|---|---|
| **Visita o site** | e-mail, whatsapp, **sem SSL**, **não responsivo**, **site lento/quebrado**, stack antiga |
| **Google PageSpeed / Lighthouse** | nota de performance/SEO baixa = precisa de site novo |
| **CNPJ enrich** (ReceitaWS/CNPJ.ws) | **negócio novo** (data de abertura), situação, CNAE, sócios, capital |
| **Instagram profile** | seguidores, **último post** (ativo vs. abandonado), tem link na bio |
| **WhatsApp check** | tem WhatsApp Business? (pré-requisito pro zapagente) |
| **E-mail verify** (MX/SMTP) | e-mail válido? |

**Recomendação de arranque (F1/F2):** CNPJ (Tier 0) como base + Google Maps (Tier 1) pra sinais + visita-ao-site (enrich). Isso já é 10× o que existe hoje, e é o núcleo defensável. O resto entra plugando fontes.

---

## 5. Motor de critérios dinâmicos — o "muda os critérios"

Um **ICP (Ideal Customer Profile)** é uma spec declarativa. É isso que você edita pra "mudar os critérios" sem tocar em código:

```python
ICP(
    nome="Salões sem site em João Pessoa",
    nicho=["salão de beleza", "cabeleireiro"],   # ou CNAE 9602-5/01
    regiao=Regiao(municipio="João Pessoa", uf="PB", raio_km=15),
    fontes=["cnpj", "google_maps"],              # quais motores usar
    filtros=Filtros(
        tem_site=False,                          # o alvo
        tem_instagram=None,                      # tanto faz
        nota_min=3.5, nota_max=None,
        min_avaliacoes=5, max_avaliacoes=None,
        aberto_apos="2023-01-01",                # negócio novo
        tem_whatsapp=True,                       # pré-req do zapagente
    ),
    pontuacao=PesosOportunidade(                 # o que vale mais pra ESTA campanha
        sem_site=5, so_redes=3, site_ruim=4,
        insta_inativo=2, negocio_novo=2,
    ),
    limite=200,
)
```

O **orquestrador** faz: escolhe fontes que atendem o ICP → descobre → **dedup/identidade** → enriquece → **pontua** cada negócio contra os pesos → devolve leads ranqueados. Cada fonte declara quais filtros resolve nativamente e quais viram pós-filtro.

O `score_digital` de hoje (0/1/2) vira um caso particular de `PesosOportunidade`. Vendendo site → peso alto em `sem_site`. Vendendo social media → peso alto em `insta_inativo`. **A mesma engine serve qualquer oferta.**

---

## 6. Pipeline de dados de verdade (lakehouse real)

Hoje o "medallion" só tem bronze. Vamos entregar as 3 camadas:

- **Bronze** — bruto, imutável, 1 arquivo por execução de fonte (JSON/Parquet em `data/bronze/<fonte>/`). Rastreável. *(Aqui o DuckDB pode ler os Parquet pra análise, se quiser manter a narrativa lakehouse.)*
- **Silver** — limpo e normalizado no Postgres: telefone E.164, nome canônico, geo, **identity resolution** (mescla o mesmo negócio vindo de Maps + CNPJ + Insta por **CNPJ → telefone normalizado → nome+geohash**).
- **Gold** — o negócio com **todos os sinais** + **score de oportunidade** calculado por ICP. É o que vira lead e vai pro zapagente.

Dedup real (hoje só existe `url_maps UNIQUE`): chave de identidade em cascata **CNPJ > telefone(E.164) > nome_normalizado+geohash**.

---

## 7. Conector FARO → zapagente

Substitui o `whatsapp_sender.py`. FARO **empurra** leads Gold pro zapagente:

```
FARO (Gold leads)
   │  autentica (JWT)
   ▼
zapagente  POST /contatos (bulk)      ← nome, telefone E.164, e-mail
           + aplica tags               ← ["faro", "sem-site", "salao", "joao-pessoa"]
           + (opcional) dispara campanha / missão IA
```

Contrato (confirmar endpoints exatos lendo o repo `zapagente` quando formos construir — memória indica Contatos-CRM + Tags TAG-1/2 + Campanhas + JWT multi-tenant):
- `ZapagenteClient.auth()` → JWT.
- `.upsert_contatos(leads)` → cria/atualiza contatos, idempotente por telefone.
- `.aplicar_tags(contato_id, tags)` → segmentação (a base da campanha por tag).
- `.disparar_campanha(tag, template)` → opcional, deixa o zapagente conduzir.

Assim as tags que o FARO gera (nicho, cidade, sinal de oportunidade) viram os **filtros de campanha** do zapagente. Encaixe limpo.

---

## 8. Estrutura de pastas (a arquitetura em disco)

```
faro/                              # (renomear repo lead-lakehouse → faro; opcional)
├── faro/
│   ├── domain/                    # PURO, sem I/O
│   │   ├── models.py              # Business, Lead, Signal, Score (Pydantic)
│   │   ├── icp.py                 # ICP, Filtros, PesosOportunidade
│   │   ├── scoring.py             # regra de pontuação
│   │   ├── identity.py            # dedup / resolução de identidade
│   │   └── sources.py             # interfaces DiscoverySource / EnrichmentSource
│   ├── sources/                   # infra — 1 arquivo por fonte
│   │   ├── cnpj.py
│   │   ├── google_maps.py         # Playwright
│   │   ├── google_places.py       # API oficial
│   │   ├── openstreetmap.py
│   │   ├── instagram.py
│   │   └── registry.py            # registro de fontes
│   ├── enrichment/
│   │   ├── site_visitor.py        # e-mail, SSL, responsivo, pagespeed
│   │   ├── cnpj_enrich.py
│   │   └── whatsapp_check.py
│   ├── pipeline/                  # bronze → silver → gold
│   ├── infra/
│   │   ├── db/                    # SQLAlchemy + Alembic (Postgres)
│   │   ├── browser.py             # BrowserPool Playwright (anti-detecção)
│   │   └── cache.py
│   ├── integrations/
│   │   └── zapagente/client.py    # o conector
│   ├── app/                       # casos de uso (orquestrador)
│   ├── interface/
│   │   ├── cli.py
│   │   └── streamlit_app.py       # reaproveita a UI atual
│   └── config.py                  # pydantic-settings
├── tests/
├── docs/PLANO.md                  # este arquivo
├── docker-compose.yml             # Postgres
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 9. Modelo de dados (resumo)

`businesses` (silver): id, tenant_id, cnpj, nome, nome_norm, categoria, cnae, telefone_e164, email, site, tem_site, redes(json), nota, n_avaliacoes, lat/lng, geohash, municipio, uf, data_abertura, situacao_cnpj, fontes(json), criado_em, atualizado_em.
`signals`: business_id, tipo (sem_site|site_ruim|insta_inativo|negocio_novo…), valor, fonte, coletado_em.
`leads` (gold): business_id, icp_id, score, oportunidade, tags(json), status (novo|enviado_zapagente|…), zapagente_contato_id.
`runs` (manifesto): id, icp, fonte, iniciado_em, terminado_em, descobertos, novos, erros, status.
`icps`: a spec da §5 persistida.

Todas com `tenant_id` (default do seu tenant) desde o dia 1.

---

## 10. Anti-detecção & escala

- **Playwright stealth** + rotação de user-agent + viewport aleatório.
- **Delays randomizados** (não fixos como os 8s atuais) + backoff.
- **Suporte a proxy** (config-driven, residencial opcional) — hook pronto, você liga quando/se precisar.
- **Concorrência** via asyncio + pool de contextos de browser (limite configurável).
- **Perfil de browser persistente** (sem baixar driver toda vez, como o `ChromeDriverManager` faz hoje).
- **Rate por fonte** respeitando cada ToS; CNPJ/Overpass aguentam volume, Insta/Maps vão devagar.

---

## 11. Legal / LGPD ⚖️ (ler)

- **Dado de empresa (B2B) é mais defensável** que dado pessoal, e **dados abertos da Receita (CNPJ) são 100% legais** — por isso são a base.
- **Scraping de Maps/Instagram viola ToS** (zona cinza) — mitigar: preferir API oficial onde der, rate baixo, uso próprio.
- **Outreach frio no WhatsApp** (B2B) se apoia em *legítimo interesse*, mas **precisa respeitar opt-out** e não pode ser spam em massa — isso vive no zapagente, que já tem anti-ban e controle. Manter tags de origem e consentimento.
- **Não versionar dados coletados** (já está no `.gitignore`; manter — CPF/telefone = LGPD).

---

## 12. Roadmap por fases

| Fase | Entrega | Resultado |
|---|---|---|
| **F0 — Fundação** | pyproject, venv 3.12, config `.env`, Postgres via docker-compose, camadas de domínio (models/ICP/interfaces), README, testes base | Casa arrumada e tipada |
| **F1 — Motor 1 fonte** | Playwright + Google Maps refeito atrás da interface `DiscoverySource`; bronze→silver→gold; dedup real; score por ICP | Paridade com hoje, porém robusto e extensível |
| **F2 — Multi-fonte** | CNPJ (base legal) + OpenStreetMap; identity resolution cruzando fontes; registry de fontes | O "muitas fontes" ligado; descoberta legal e massiva |
| **F3 — Enriquecimento + score** | visita-site (e-mail/SSL/responsivo/pagespeed) + CNPJ enrich + whatsapp check; `PesosOportunidade` completo | Leads ricos e bem ranqueados |
| **F4 — Conector zapagente** | `ZapagenteClient`: auth + upsert contatos + tags + (opcional) campanha. **Remove `whatsapp_sender.py`.** | Leads fluem pro motor de conversão |
| **F5 — Produto/UI** | Streamlit refeito (editor de ICP, monitor de runs, painel de leads/score, botão "enviar pro zapagente"); CLI | Ferramenta pronta pra uso diário |
| **F6 — (futuro) SaaS** | FastAPI + fila Arq/Redis + auth + multi-tenant real + billing | Vira produto vendável |

---

## 13. O que muda no repo atual (v0.6 → FARO)

- `scraper/google_maps_scraper.py` → vira `sources/google_maps.py` (Playwright, atrás de interface). Lógica de score/sinônimos aproveitada.
- `pipelines/bronze_pipeline.py` → vira `pipeline/` com bronze/silver/gold reais.
- `db/database.py` (DuckDB) → `infra/db/` (Postgres + Alembic). *(ou mantém DuckDB — decisão aberta A.)*
- `outreach/whatsapp_sender.py` → **removido**, substituído por `integrations/zapagente/`.
- `main.py` (Streamlit) → `interface/streamlit_app.py`, reaproveitando o CSS/layout bonito que já existe.
- Adiciona: README, `.env.example`, `pyproject.toml`, `docker-compose.yml`, testes.

---

## 14. Riscos & mitigação

| Risco | Mitigação |
|---|---|
| Google/Insta mudam o HTML | Parsers isolados + testes contra HTML salvo; preferir API oficial/CNPJ como base |
| Ban de IP/conta | Rate baixo, proxy opcional, começar por fontes sem ToS (CNPJ/OSM) |
| Escopo grande | Roadmap por fases; cada fase entrega algo usável |
| LGPD / ToS | Base em dado aberto, opt-out no zapagente, nada de dado versionado |
| Custo (Places API/proxy) | Opcionais, ligados por config só quando precisar |

---

## 15. Decisões abertas (me confirme)

- **A.** Banco: **Postgres desde já** (recomendo, multi-tenant-ready) ou seguir no DuckDB e migrar depois?
- **B.** Renomear o repo `lead-lakehouse` → `faro` (o produto é FARO) ou manter o nome do repo?
- **C.** Ordem de arranque das fontes na F2: confirmo **CNPJ + Google Maps + visita-site** como o núcleo, e o resto entra plugando. Ok?
- **D.** Proxy/Places API: deixo os hooks prontos mas **desligados** por padrão (custo zero até você querer). Ok?

Aprovando isto (com as respostas de A–D), começo pela **F0 — Fundação**.
