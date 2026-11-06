# StartupForge AI

A multi-agent AI startup builder. You describe a startup idea, a LangGraph pipeline of seven Groq-powered agents researches it on the web, and a React dashboard streams each agent's progress live (Server-Sent Events) before showing the finished brief: market, competitors, product plan, financial projections, fact check, and sources.

**Pipeline:** Search → Research → Competitor → Product → Finance → Report → Critic

## Grounding: how fabrication is prevented

Prompts ask the agents not to invent anything, but the important guarantees are **enforced in code**:

| Risk | Guard |
|---|---|
| Fake sources | Every source is a passage of a page actually returned by Tavily. Titles, URLs, and text are never LLM-written. |
| Citations to nothing | `app/citations.py` strips any `[n]` marker that doesn't match a source shown to that agent. |
| Citations that don't back the claim | The **Critic** compares each cited claim with the exact passage. Citations judged unsupported are removed, and every verdict is listed in the Fact check tab. |
| Invented statistics | Every `$`, `%`, or "million/billion" figure is checked in code against the text of its cited source (or the financial model). Missing ones are flagged. |
| Invented competitors | A competitor is kept only if its name appears in a source it cites; others are listed as omitted. |
| Made-up financials | The LLM only proposes assumptions. All projections come from `app/finance.py` (plain, unit-tested arithmetic), and edits are recomputed on the server. |
| No sources at all | Without web search the report says so, has no citations, and is marked `llm_knowledge_unverified`. |

**Limits:** the critic is itself an LLM, so its verdicts can be wrong; figure checks match numbers, not meaning. Claims beyond the first 24 are marked "not checked". The UI tells readers to open sources for anything important.

## Agents

| Agent | Does | Code-level checks |
|---|---|---|
| Search | Plans market + competitor queries, fetches pages (Tavily), chunks and indexes them | dedupe by URL |
| Research | Customers, pain points, trends, risks, from its top-k retrieved passages | invalid markers stripped |
| Competitor | Competitors, alternatives, gaps | name must appear in cited source |
| Product | MVP features (must/should/could), journey, metrics, pricing options | sees no sources, so all markers stripped |
| Finance | Proposes assumptions with rationale | clamped to valid ranges; projections computed deterministically |
| Report | Founder brief | may only quote figures from the computed model |
| Critic | Fact-checks citations and figures | applies verdicts, flags figures |

## RAG

Search requests full page text from Tavily. Each page (first 8,000 chars) is split into ~800-char overlapping chunks, embedded **locally** with [fastembed](https://github.com/qdrant/fastembed) (`BAAI/bge-small-en-v1.5`, 384-d; no API key, the model downloads once, ~70 MB), and stored in **pgvector** (or in memory without a database). Each agent retrieves the passages most relevant to its own task, so a citation points to the exact passage the agent read. If embedding fails, the pipeline falls back to Tavily's short excerpts and says so.

## Financial model

```
new_m       = new_customers_month_1 × (1 + growth)^(m−1)
customers_m = customers_{m−1} × (1 − churn) + new_m
MRR_m       = customers_m × price
net_m       = MRR_m × gross_margin − new_m × CAC − fixed_costs
cash_m      = cash_{m−1} + net_m
LTV = price × margin / churn,  CAC payback = CAC / (price × margin)
```

Scenarios use fixed multipliers: conservative = acquisition ×0.75, growth ×0.5, churn ×1.5; optimistic = acquisition ×1.25, growth ×1.5, churn ×0.75.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19 (JavaScript/JSX), Vite, Tailwind CSS v4, Framer Motion, React Router, Axios, Lucide React, Recharts, Geist font |
| Backend | Python 3.12+, FastAPI, LangGraph, LangChain, Groq (`langchain-groq`), Tavily (`httpx`), SSE (`sse-starlette`) |
| Data | PostgreSQL 16 + pgvector (`psycopg`, `pgvector`), fastembed |

## Run with Docker

```bash
cp backend/.env.example backend/.env      # set GROQ_API_KEY and TAVILY_API_KEY
docker compose up --build
```

Open http://localhost:8080. Compose starts `pgvector/pgvector:pg16`, the backend (embedding model baked into the image), and the frontend behind nginx (SSE buffering disabled).

## Run locally (without Docker)

### Prerequisites

- **Python 3.12+** (`python --version`)
- **Node.js 20+** and npm (`node --version`)
- A **Groq API key** (required): https://console.groq.com/keys
- A **Tavily API key** (optional but recommended, for web search and real citations): https://app.tavily.com
- *Optional:* Docker or a local PostgreSQL 16 with pgvector, if you want reports to persist

### 1. Clone the repository

```bash
git clone https://github.com/ShubhodLoni/StartupForge StartupForge
cd StartupForge
```

### 2. Start the backend (terminal 1)

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env          # then edit .env: set GROQ_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**macOS / Linux:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then edit .env: set GROQ_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --reload --port 8000
```

The API is now on http://localhost:8000 (interactive docs at http://localhost:8000/docs). The first run downloads the embedding model (~70 MB), so it can take a little longer.

### 3. Start the frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to `http://localhost:8000` (override with `VITE_PROXY_TARGET`). The badges in the top right show whether the backend is reachable, Groq is configured, and web search is on.

### 4. (Optional) Persist data with PostgreSQL + pgvector

Without `DATABASE_URL`, reports and vectors are kept in memory and lost when the backend restarts. To persist them, start a pgvector database, for example with Docker:

```bash
docker run -d --name startupforge-db -p 5432:5432 -e POSTGRES_USER=startupforge -e POSTGRES_PASSWORD=startupforge -e POSTGRES_DB=startupforge pgvector/pgvector:pg16
```

Then uncomment this line in `backend/.env` and restart the backend. Tables are created automatically.

```
DATABASE_URL=postgresql://startupforge:startupforge@localhost:5432/startupforge
```

### Troubleshooting

- **"Groq not configured" badge:** check `GROQ_API_KEY` in `backend/.env`, then restart uvicorn.
- **Web search off:** set `TAVILY_API_KEY`. Without it, reports run on LLM knowledge only and are marked unverified.
- **CORS errors:** if the frontend runs on a different origin than `http://localhost:5173`, add it to `CORS_ORIGINS` in `backend/.env`.
- **Port already in use:** change `--port 8000` (and set `VITE_PROXY_TARGET` to match), or stop the other process.
- **Rate limits:** a run makes 7 LLM calls. On Groq's free tier you may hit per-minute token limits; the client retries with backoff, so some runs take longer.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Keys configured, storage (`postgres`/`memory`), RAG on/off, agent list |
| POST | `/api/reports/stream` | Run the pipeline, streamed as SSE: `agent_started`, `agent_completed`, `complete`, `error` |
| POST | `/api/reports` | Same, as a single JSON response |
| GET | `/api/reports` | Recent reports |
| GET | `/api/reports/{id}` | One report |
| PUT | `/api/reports/{id}/finance` | Recompute (server-side) and save edited financial assumptions |
| POST | `/api/finance/projection` | Stateless deterministic projection |

Interactive docs: http://localhost:8000/docs

## Tests

```powershell
cd backend;  .\.venv\Scripts\python -m pytest -q    # fake LLM, fake search, hash embedder: no keys needed
cd frontend; npm test                               # Vitest + Testing Library
```

Postgres integration tests run when `TEST_DATABASE_URL` points to a database with pgvector, and clean up after themselves:

```powershell
$env:TEST_DATABASE_URL = "postgresql://user:pass@localhost:5432/startupforge"; pytest tests/test_postgres.py
```

## Layout

```
backend/app/
  main.py         FastAPI app, services (Postgres or memory), REST + SSE endpoints
  graph.py        LangGraph pipeline and per-agent retrieval
  agents/         search, research, competitor, product, finance, report, critic
  rag.py          chunking, embeddings, in-memory index, per-run retriever, source registry
  db.py           PostgreSQL: pgvector index + report store
  citations.py    [n] marker validation
  finance.py      deterministic financial engine
  search.py       Tavily client
frontend/src/
  pages/          NewReportPage, ReportPage
  components/     Layout, IdeaForm, AgentProgress, ReportView, CitedText, HealthBadge
    report/       Overview/Market/Competitors/Product/Sources panels, FinancePanel, FactCheckPanel
  api/client.js   Axios + fetch-based SSE
  lib/            SSE parser, agent metadata, formatting, local report cache
docker-compose.yml
```
