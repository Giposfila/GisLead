# AGENT.md — LeadGis Implementation Guide

> Instructions for AI coding agents (Claude Code, Cursor, Copilot Workspace, etc.) implementing this project.
> Read this file fully before writing any code. When in doubt, follow the conventions here over your defaults.

---

## 1. Project overview

**LeadGis** is a fully local, open-source lead-generation desktop tool. It runs entirely on the user's machine — no vendor server, no telemetry, no accounts.

What it does:

1. Collects business listings from 2GIS by niche + city (official Catalog API first, optional Playwright scraper as a fallback).
2. Enriches each lead: website presence check, WhatsApp/Telegram/Instagram links, rating/review data.
3. Generates a personalized outreach message per lead using an LLM (cloud APIs via user-provided keys, or local models via Ollama).
4. Presents leads in a mini-CRM web UI (`localhost:8000`) with one-click `wa.me` send links and status tracking.
5. Exports to CSV/XLSX.

**What it deliberately does NOT do:**

- No fully automated WhatsApp/Telegram mass-sending in core. Sending is **semi-automatic**: the app opens a prefilled `wa.me` / `t.me` link; the human clicks send. This is a product decision (account-ban risk + anti-spam law compliance), not a technical limitation. Do not implement whatsapp-web.js/Baileys/Telethon-style automation in the core package.
- No payment, licensing, or account systems.
- No data collection about the user.

**Target user:** freelancers, web studios, and small agencies in CIS markets. UI language: Russian. Code, comments, commits, docs for developers: English.

---

## 2. Tech stack (fixed — do not substitute)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python ≥ 3.11 | Use modern typing (`X | None`, `Self`, `StrEnum`) |
| Backend | FastAPI + uvicorn | Single process |
| Async | asyncio + httpx | All I/O is async. No `requests`, no threads for I/O |
| DB | SQLite via SQLAlchemy 2.0 (async, `aiosqlite`) | DB file at `~/.leadgis/leadgis.db` |
| Migrations | Alembic | Auto-run on startup |
| Background jobs | In-process `asyncio` workers + `asyncio.Queue` | **No Celery, no Redis** — this is a local app |
| Progress to UI | Server-Sent Events (SSE) | Not WebSockets (simpler, enough) |
| Frontend | Vite + React + TypeScript | Served as static build by FastAPI in prod; dev proxy in dev |
| UI kit | Tailwind CSS; keep deps minimal | No heavy component libraries |
| Scraper (optional extra) | Playwright (chromium) | Installed only via `pip install leadgis[scraper]` |
| LLM clients | `httpx` directly (OpenAI-compatible) + official `anthropic` SDK | Do **not** add LangChain |
| Config | TOML at `~/.leadgis/config.toml` + env overrides | `pydantic-settings` |
| Packaging | `pyproject.toml` (hatchling), entry point `leadgis` | Also provide Dockerfile + docker-compose.yml |
| Tests | pytest + pytest-asyncio + respx (httpx mocking) | Coverage target ≥ 80% on core modules |
| Lint/format | ruff (lint + format), mypy (strict on `leadgis/` core) | CI must pass both |

---

## 3. Repository layout

```
leadgis/
├── AGENT.md                     # this file
├── README.md                    # user-facing, Russian + English quickstart
├── LICENSE                      # MIT
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml     # lint, typecheck, tests on 3.11/3.12
├── leadgis/
│   ├── __init__.py              # __version__
│   ├── main.py                  # create_app(), uvicorn entry, opens browser
│   ├── cli.py                   # `leadgis start|export|reset` (typer)
│   ├── config.py                # Settings (pydantic-settings), config.toml loader
│   ├── constants.py             # niches catalog, defaults
│   ├── db/
│   │   ├── engine.py            # async engine/session factory
│   │   ├── models.py            # ORM models (see §5)
│   │   └── migrations/          # alembic
│   ├── sources/
│   │   ├── base.py              # DataSource ABC + DTOs
│   │   ├── twogis_api.py        # official Catalog API adapter
│   │   ├── twogis_scraper.py    # Playwright adapter (extra)
│   │   └── registry.py          # source discovery/selection
│   ├── enrichment/
│   │   ├── website.py           # liveness/quality check
│   │   └── messengers.py        # wa.me / t.me / instagram link builders
│   ├── llm/
│   │   ├── base.py              # LLMProvider ABC
│   │   ├── openai_compat.py     # OpenAI, Ollama, Groq, OpenRouter, LM Studio
│   │   ├── anthropic_provider.py
│   │   └── registry.py
│   ├── generation/
│   │   ├── generator.py         # batch message generation
│   │   └── prompts/
│   │       ├── outreach_ru.md   # default template (Russian output)
│   │       └── outreach_en.md
│   ├── services/
│   │   ├── campaigns.py         # orchestration: collect → enrich → store
│   │   ├── leads.py             # CRUD, filtering, status transitions
│   │   └── export.py            # CSV/XLSX
│   ├── worker.py                # job queue, JobRunner, SSE event bus
│   ├── ratelimit.py             # token-bucket limiter
│   └── api/
│       ├── router.py            # mounts all routers
│       ├── campaigns.py
│       ├── leads.py
│       ├── settings.py
│       ├── events.py            # SSE endpoint
│       └── schemas.py           # Pydantic request/response models
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── pages/               # Campaigns, Leads, Settings
│       ├── components/
│       ├── api/client.ts        # typed fetch wrapper
│       └── i18n/ru.ts
└── tests/
    ├── conftest.py              # tmp DB, respx fixtures
    ├── test_sources/
    ├── test_llm/
    ├── test_services/
    └── test_api/
```

---

## 4. Architecture rules

1. **Adapter pattern everywhere external.** Data sources and LLM providers are pluggable behind ABCs. Core services depend only on the ABCs. Adding "Yandex Maps source" or "Mistral provider" must require zero changes to services.
2. **All external calls go through the rate limiter** (`ratelimit.py`). Never call 2GIS or an LLM API directly from a service without a limiter handle.
3. **Everything long-running is a Job.** Collection and generation run as background jobs with persisted state (`jobs` table) and emit progress events over SSE. API endpoints must return immediately with a `job_id`.
4. **The DB is the source of truth.** The frontend is a thin view; no business logic in React beyond display/filtering already-fetched data.
5. **Graceful degradation.** If the LLM is unavailable → leads still collected, generation marked failed per-lead with a retriable error. If enrichment fails → lead saved with `website_status=unknown`.
6. **No secrets in the DB or logs.** API keys live only in `config.toml` (chmod 600). Redact keys in any log/error output (`sk-***`).

---

## 5. Data model (SQLAlchemy ORM)

Implement exactly these tables (add columns if needed, don't remove):

```python
class Campaign(Base):
    id: Mapped[int]                    # pk
    name: Mapped[str]
    niche: Mapped[str]                 # free text or catalog key
    city: Mapped[str]
    source: Mapped[str]                # "twogis_api" | "twogis_scraper"
    status: Mapped[str]                # StrEnum: draft|collecting|ready|failed
    created_at: Mapped[datetime]
    leads: relationship -> Lead

class Lead(Base):
    id: Mapped[int]
    campaign_id: Mapped[int]           # fk, index
    external_id: Mapped[str | None]    # 2GIS org id; unique per campaign
    name: Mapped[str]
    category: Mapped[str | None]
    address: Mapped[str | None]
    phone_e164: Mapped[str | None]     # normalized +79991234567
    phones_raw: Mapped[str | None]     # JSON list, as returned by source
    website: Mapped[str | None]
    website_status: Mapped[str]        # StrEnum: none|dead|alive|unknown
    whatsapp_url: Mapped[str | None]   # https://wa.me/7999...
    telegram_url: Mapped[str | None]
    instagram_url: Mapped[str | None]
    rating: Mapped[float | None]
    reviews_count: Mapped[int | None]
    status: Mapped[str]                # StrEnum: new|message_ready|sent|replied|client|rejected
    raw_json: Mapped[str | None]       # full source payload for debugging
    created_at / updated_at

class Message(Base):
    id: Mapped[int]
    lead_id: Mapped[int]               # fk, index
    text: Mapped[str]
    provider: Mapped[str]              # "anthropic" | "openai_compat:ollama" ...
    model: Mapped[str]
    prompt_template: Mapped[str]       # template filename used
    tokens_in / tokens_out: Mapped[int | None]
    created_at: Mapped[datetime]
    is_current: Mapped[bool]           # latest generation for the lead

class Job(Base):
    id: Mapped[str]                    # uuid4 hex, pk
    kind: Mapped[str]                  # "collect" | "generate" | "enrich"
    campaign_id: Mapped[int | None]
    status: Mapped[str]                # queued|running|done|failed|cancelled
    progress: Mapped[int]              # 0..100
    detail: Mapped[str | None]         # human-readable current step / error
    created_at / finished_at
```

Phone normalization: strip everything to digits, map leading `8` → `+7` for RU/KZ formats, store E.164. Put this in a pure function `normalize_phone(raw: str, default_region: str = "RU") -> str | None` with exhaustive unit tests. Prefer the `phonenumbers` library.

---

## 6. Data sources

### 6.1 `DataSource` ABC (`sources/base.py`)

```python
@dataclass(slots=True)
class OrgDTO:
    external_id: str | None
    name: str
    category: str | None
    address: str | None
    phones: list[str]
    website: str | None
    instagram: str | None
    telegram: str | None
    rating: float | None
    reviews_count: int | None
    raw: dict

class DataSource(ABC):
    id: ClassVar[str]                  # "twogis_api"
    display_name: ClassVar[str]
    requires: ClassVar[list[str]]      # config keys needed, e.g. ["twogis_api_key"]

    @abstractmethod
    def search(self, niche: str, city: str, limit: int) -> AsyncIterator[OrgDTO]: ...
    @abstractmethod
    async def healthcheck(self) -> HealthStatus: ...
```

`search` is an **async generator** — yield leads as they arrive so the UI fills progressively.

### 6.2 2GIS Catalog API adapter

- Base: `https://catalog.api.2gis.com/3.0/items` with `q={niche} {city}` or `q={niche}` + `city_id` (resolve city via `/2.0/region/search` once, cache in DB `kv` table).
- Request fields param must include: `items.contact_groups,items.reviews,items.name_ex,items.address,items.rubrics,items.point`.
- Pagination via `page`/`page_size` (max 50). Respect `meta.total`.
- Extract from `contact_groups`: phones (`type == "phone"`), website (`type == "website"`), instagram/telegram/whatsapp entries when present.
- Rate limit: default 5 req/s, configurable. On HTTP 403/429: exponential backoff (1s, 2s, 4s, max 3 retries), then fail the job with a clear message ("2GIS key exhausted or invalid").
- The API key comes from user config. Document in README how to obtain a key from dev.2gis.com and that free tier limits apply.

### 6.3 Playwright scraper adapter (optional extra)

- Only importable when `leadgis[scraper]` extras installed; `registry.py` must handle ImportError and hide the source from the UI.
- Navigate `https://2gis.<tld>/search/{query}`, scroll the results panel, parse cards; open card pages for contacts only when the list card lacks them.
- Hard limits: max 1 page action per 1.5–3s (randomized), max 200 orgs per run, honest User-Agent.
- Wrap all selectors in one `selectors.py` module — they will break; make them trivially updatable.
- Show a persistent UI warning when this source is selected: "Scraping may violate 2GIS ToS; use the official API when possible. You proceed at your own risk." Also state this in README.

---

## 7. Enrichment

### 7.1 Website check (`enrichment/website.py`)

```
async def check_website(url: str | None) -> WebsiteStatus
```
- `None`/empty → `none`.
- Normalize scheme (try https, fallback http). `HEAD`, fallback `GET` (some servers reject HEAD), timeout 8s, follow ≤ 3 redirects.
- 2xx/3xx → `alive`; connection error / 4xx / 5xx → `dead`; timeout → `unknown`.
- Treat social-network links (vk.com, instagram.com, taplink, t.me) as `website_status=none` but keep the link — "has only a social page" is exactly the sales signal this tool targets. Keep a configurable list of such domains in `constants.py`.
- Run checks with `asyncio.Semaphore(10)`.

### 7.2 Messenger links (`enrichment/messengers.py`)

- WhatsApp: from E.164 phone → `https://wa.me/<digits>`; with message → `?text=<urlencoded>`. Do not verify WA registration (no reliable unauthenticated way) — name the field honestly (`whatsapp_url`, not `has_whatsapp`).
- Telegram: only if source provided a username/link.
- Pure functions, fully unit-tested.

---

## 8. LLM layer

### 8.1 `LLMProvider` ABC (`llm/base.py`)

```python
class LLMProvider(ABC):
    id: ClassVar[str]

    @abstractmethod
    async def complete(self, system: str, user: str, *,
                       max_tokens: int = 1024,
                       temperature: float = 0.8) -> LLMResult: ...
    @abstractmethod
    async def healthcheck(self) -> HealthStatus: ...
    @abstractmethod
    async def list_models(self) -> list[str]: ...

@dataclass(slots=True)
class LLMResult:
    text: str
    tokens_in: int | None
    tokens_out: int | None
    model: str
```

### 8.2 OpenAI-compatible provider (`llm/openai_compat.py`)

One class covers OpenAI, Ollama, LM Studio, Groq, OpenRouter, DeepSeek — differing only by config:

```toml
[llm]
provider = "openai_compat"
base_url = "http://localhost:11434/v1"   # Ollama default
api_key  = ""                            # empty OK for Ollama
model    = "qwen2.5:14b"
```

- POST `{base_url}/chat/completions`; parse `choices[0].message.content` and `usage`.
- `list_models`: GET `{base_url}/models`; for Ollama additionally try native `GET /api/tags` for better metadata.
- Ollama healthcheck: if base_url points at :11434 and model missing from tags → return actionable error: `Model not found. Run: ollama pull qwen2.5:14b`.
- Timeouts: connect 5s; read 120s for local models (CPU inference is slow), 60s cloud.

### 8.3 Anthropic provider

- Official `anthropic` async SDK, `messages.create`. Default model configurable, sensible default in `constants.py`.
- Map SDK exceptions to the common error taxonomy below.

### 8.4 Common error taxonomy

Define in `llm/base.py`: `AuthError`, `RateLimitError(retry_after)`, `ModelNotFoundError`, `ProviderUnavailable`, `GenerationError`. Providers must translate their raw errors into these; services and UI handle only these five.

---

## 9. Message generation

### 9.1 Prompt templates (`generation/prompts/*.md`)

Templates are user-editable markdown with `{placeholders}`; agent must implement rendering via `str.format_map` over a safe dict (missing key → empty string, never crash). Default `outreach_ru.md`:

```markdown
# system
You write short first-touch WhatsApp messages in Russian for B2B outreach
from a web studio to small local businesses. Rules:
- 2–4 sentences, no greetings like "Уважаемый", no emoji, no links.
- Mention the business by name naturally, reference one concrete detail
  (rating, reviews, or missing website) without flattery.
- End with one simple question. Never sound like a template or mass mailing.
- Output ONLY the message text, nothing else.

# user
Business: {name}
Category: {category}
City: {city}
Rating: {rating} ({reviews_count} reviews)
Website: {website_status_human}
Our service: {user_offer}
Extra instructions: {extra_instructions}
```

- `user_offer` and `extra_instructions` come from campaign settings.
- Parse the `# system` / `# user` sections; validate template on save.

### 9.2 Batch generator (`generation/generator.py`)

- Job over selected lead IDs. Concurrency: `asyncio.Semaphore(cfg.llm_concurrency)` — default 2 for cloud, 1 for Ollama.
- Per-lead: render → `provider.complete` → post-process (trim, strip quotes/markdown fences, enforce ≤ 600 chars — regenerate once at temperature 0.6 if longer) → save `Message(is_current=True)`, flip previous to `False`, set lead status `message_ready`.
- On `RateLimitError`: wait `retry_after` (default 20s), retry ≤ 3. On repeated failure: mark that lead's generation failed, continue batch — one bad lead must not kill the job.
- Emit SSE progress after every lead: `{job_id, done, total, current_lead_name}`.

---

## 10. Jobs, queue, SSE (`worker.py`)

- Single global `JobRunner` started in FastAPI lifespan. `asyncio.Queue[JobSpec]`, N worker tasks (default 1 — jobs are internally concurrent).
- Job state persisted to DB on every transition; on startup, mark `running` jobs from a previous crash as `failed (interrupted)`.
- Cancellation: `POST /api/jobs/{id}/cancel` sets a flag; jobs check it between units of work.
- Event bus: in-memory pub/sub; `GET /api/events` streams SSE (`event: job_progress`, JSON data). Heartbeat comment every 15s.

---

## 11. HTTP API (all under `/api`)

| Method & path | Purpose |
|---|---|
| `GET  /settings` / `PUT /settings` | Read/update config (keys write-only: never returned, only `is_set: true`) |
| `POST /settings/test/source` | Healthcheck selected data source |
| `POST /settings/test/llm` | Healthcheck LLM + tiny test completion |
| `GET  /sources` | Available sources with `available: bool` + missing requirements |
| `GET  /llm/models` | Models list from active provider |
| `POST /campaigns` | Create campaign |
| `GET  /campaigns` / `GET /campaigns/{id}` | List/detail with lead counts by status |
| `POST /campaigns/{id}/collect` | Start collect job → `{job_id}` |
| `GET  /campaigns/{id}/leads` | Filter: `status`, `website_status`, `has_phone`, search `q`; paginate |
| `PATCH /leads/{id}` | Update status / edit fields |
| `POST /leads/{id}/generate` / `POST /campaigns/{id}/generate` | Generate for one / for filtered set → `{job_id}` |
| `PUT  /leads/{id}/message` | Manual edit of current message text |
| `GET  /leads/{id}/wa-link` | Final wa.me URL with urlencoded current message |
| `GET  /campaigns/{id}/export?format=csv|xlsx` | Download export |
| `GET  /events` | SSE stream |
| `GET  /jobs/{id}` / `POST /jobs/{id}/cancel` | Job status / cancel |

Bind to `127.0.0.1` by default. If config sets `host = "0.0.0.0"`, require `auth_token` in config and enforce `Authorization: Bearer` on `/api/*` (protects LAN exposure).

---

## 12. Frontend requirements

Pages:
1. **Settings** — source picker + key inputs; LLM provider picker (presets: Ollama / OpenAI / Anthropic / OpenRouter / Custom base URL) with model dropdown from `/llm/models`; "Test connection" buttons with clear success/failure toasts.
2. **Campaigns** — list with status chips; create dialog (niche autocomplete from `constants.py` catalog of 100+ niches, free text allowed; city; source; limit).
3. **Leads** (main screen) — table: name, category, rating/reviews, phone, website badge (`none` = green "no website" — it's the sales signal), status. Filters mirror the API. Row expands to a card: full data, current message in editable textarea, buttons **Regenerate**, **Open WhatsApp** (opens `wa-link` in new tab, then auto-prompts "Mark as sent?"), status dropdown.
4. Global: live progress bar strip driven by SSE; job errors surface as toasts with the `detail` text verbatim.

UX rules: Russian UI strings centralized in `i18n/ru.ts`; every failure state must render an actionable message (what happened + what to do), never a bare "Error".

---

## 13. Config file (`~/.leadgis/config.toml`)

```toml
[app]
host = "127.0.0.1"
port = 8000
open_browser = true

[source]
active = "twogis_api"
twogis_api_key = ""

[source.scraper]
enabled = false
max_orgs = 200

[llm]
provider = "openai_compat"        # or "anthropic"
base_url = "http://localhost:11434/v1"
api_key = ""
model = "qwen2.5:14b"
concurrency = 2

[limits]
twogis_rps = 5
website_check_concurrency = 10

[outreach]
user_offer = ""                   # e.g. "Делаем сайты для локального бизнеса от 90 000 ₸ за 7 дней"
template = "outreach_ru.md"
```

Created with defaults on first run. `leadgis start` prints the path. Env overrides: `LEADGIS_LLM__API_KEY` style (pydantic-settings nested delimiter `__`).

---

## 14. Legal / ethical guardrails (must be implemented, not just documented)

1. Semi-automatic sending only (see §1). Do not add auto-send even if a future issue/PR requests it for the core; point to a plugin architecture instead.
2. Scraper adapter: opt-in extra, ToS warning in UI and README (see §6.3).
3. README must include a compliance section: user is responsible for anti-spam laws in their jurisdiction (e.g., RU Federal Law "On Advertising" art. 18 — consent requirements for ad messages; similar rules in KZ/BY), and for 2GIS API terms.
4. Rate limits are defaults-on, not opt-in.
5. No dark patterns: exports contain only data the user collected; no hidden fields.

---

## 15. Coding conventions

- Python: ruff default rules + `I` (isort) + `ASYNC`; line length 100. `mypy --strict` on `leadgis/` (tests may relax).
- Full type hints everywhere; DTOs are `@dataclass(slots=True)` or Pydantic models at API boundary — never raw dicts across module boundaries.
- Errors: raise the taxonomy exceptions; a single exception handler in `api/router.py` maps them to HTTP (401→"key invalid", 429→"rate limited, retry in Ns", 502→"provider unavailable", etc.).
- Logging: `structlog` or stdlib logging with a single configured formatter; INFO for job lifecycle, DEBUG for HTTP payloads (redacted). Never log full API keys or full generated messages at INFO.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`...). Small PRs per milestone step.
- Every module in §6–§10 ships with tests in the same PR that introduces it. External HTTP mocked with `respx`; include one recorded 2GIS sample response as a JSON fixture.
- Docstrings: Google style on all public functions/classes.

---

## 16. Implementation milestones (build in this order)

**M1 — Skeleton (target: app boots)**
- pyproject, config, DB engine + models + alembic, FastAPI app factory, CLI `leadgis start`, CI pipeline, empty React shell served.
- DoD: `leadgis start` opens browser, `/api/settings` round-trips, tests green.

**M2 — Collection**
- `DataSource` ABC, 2GIS API adapter, rate limiter, campaigns service + endpoints, Job runner + SSE, Leads table UI (read-only).
- DoD: create campaign → collect → leads stream into UI with live progress; key errors show actionable toast.

**M3 — Enrichment + lead management**
- Website check, messenger links, phone normalization, lead filters, status transitions, PATCH endpoints, lead card UI.
- DoD: filter "no website + has phone" works end to end.

**M4 — LLM + generation**
- Provider ABC, openai_compat + anthropic, healthchecks, model listing, prompt templates, batch generator, message UI (edit/regenerate), wa.me link flow.
- DoD: full happy path with Ollama and with one cloud provider; failure taxonomy verified by tests.

**M5 — Export + polish**
- CSV/XLSX export, niches catalog, settings UX polish, empty states, README (RU+EN), Dockerfile, `pipx` install path verified.
- DoD: a non-developer can install and reach first generated message in < 10 minutes following README.

**M6 (post-v1, do not start unless asked)**
- Scraper extra, plugin entry points (`leadgis.sources` / `leadgis.llm` via importlib.metadata), Yandex Maps source, PyInstaller build.

---

## 17. Definition of done (global)

A change is done when: code + tests + types pass CI; user-facing behavior reachable from the UI; errors actionable; README updated if setup changed; no TODOs left without a linked issue reference.
