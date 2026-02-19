# Resume Tailor

JD-optimized PDF resume generator. Upload a LaTeX resume, paste a job description, get a tailored resume with skills reordered, keywords injected, and projects prioritized.

**Core rule:** The system never adds skills the candidate doesn't have. It only reorders and emphasizes existing skills to match the JD.

## How It Works

```
User uploads .tex + pastes JD
              │
       ┌──────┴──────┐
       ▼              ▼              ← parallel (asyncio.gather)
   Step 0          Step 1
   Analyze .tex    Extract JD
   (LLM)           (LLM)
       │              │
       │   ┌──────────┘
       ▼   ▼
     Step 2: Match                   ← LLM semantic matching
       │
       ▼
     Step 3: Reorder                 ← deterministic Python
       │
       ▼
     Step 4: Inject                  ← deterministic Python
       │
       ▼
     Step 5: Compile PDF             ← pdflatex
```

| Step | Service | What | LLM? |
|------|---------|------|------|
| 0 | `resume_analyzer.py` | Insert comment markers into uploaded .tex, extract skills by category | Yes |
| 1 | `extractor.py` | Parse JD into structured keywords (languages, backend, frontend, ai_llm, databases, devops) | Yes |
| 2 | `matcher.py` | Semantically match JD keywords against resume skills (handles aliases, abbreviations, concept matching) | Yes |
| 3 | `reorderer.py` | Sort skills categories by match count, prioritize projects by keyword overlap, generate tailored summary | No |
| 4 | `injector.py` | Apply reorder plan to LaTeX, inject matched keywords, generate unified diff | No |
| 5 | `compiler.py` | Compile modified .tex to PDF via pdflatex | No |

Steps 0 and 1 run in parallel since they analyze different documents (resume vs JD).

## Architecture

```
resume-tailor/
├── backend/               Python FastAPI (port 8001)
│   ├── app/
│   │   ├── main.py                  FastAPI app, middleware, exception handlers
│   │   ├── middleware.py            Request ID middleware (contextvars)
│   │   ├── config.py                Pydantic settings from .env
│   │   ├── models.py                Pydantic schemas + ResumeSections TypedDict
│   │   ├── core/
│   │   │   ├── constants.py         All magic numbers (limits, timeouts, sizes)
│   │   │   ├── langfuse_client.py   Prompt fetching + @observe tracing
│   │   │   ├── llm.py              OpenAI + Gemini fallback client
│   │   │   ├── logger.py           Structured logger with request_id
│   │   │   └── fallback_prompts.py Embedded fallback for Langfuse-down
│   │   ├── services/
│   │   │   ├── resume_analyzer.py  Step 0: Analyze uploaded .tex
│   │   │   ├── extractor.py        Step 1: LLM keyword extraction
│   │   │   ├── matcher.py          Step 2: LLM semantic matching
│   │   │   ├── reorderer.py        Step 3: Compute reorder plan
│   │   │   ├── injector.py         Step 4: Modify LaTeX
│   │   │   └── compiler.py         Step 5: pdflatex → PDF
│   │   ├── latex/
│   │   │   ├── parser.py           Parse .tex by comment markers
│   │   │   └── writer.py           Write modified .tex sections
│   │   └── routes/
│   │       ├── tailor.py            POST /api/tailor + /api/tailor-stream (SSE)
│   │       └── health.py            GET /api/health (version + uptime)
│   ├── tests/                       207 tests (pytest + pytest-asyncio)
│   ├── scripts/
│   │   └── push_prompts.py          Push/update prompts in Langfuse
│   ├── Dockerfile                   Non-root user, HEALTHCHECK
│   ├── .dockerignore
│   ├── requirements.txt             Production deps
│   ├── requirements-dev.txt         + test deps (pytest, pytest-cov)
│   └── pyproject.toml               pytest + coverage config
│
├── frontend/              Next.js 15 + React 19 + Tailwind v4 (port 3001)
│   ├── Dockerfile                    Multi-stage build (standalone output)
│   ├── .dockerignore
│   ├── next.config.ts               Security headers, output: "standalone"
│   └── src/
│       ├── app/
│       │   ├── layout.tsx           Inter font, OG meta, favicon
│       │   └── page.tsx             Two-panel layout (input | results)
│       ├── components/
│       │   ├── jd-input-panel.tsx   File upload + JD textarea + metadata (memo'd)
│       │   ├── results-panel.tsx    Composes all result components
│       │   ├── match-score.tsx      SVG circular progress ring
│       │   ├── keyword-chips.tsx    Matched/missing/injectable chips
│       │   ├── reorder-info.tsx     Skills order, project order, summary
│       │   ├── diff-view.tsx        Collapsible LaTeX diff viewer
│       │   ├── download-button.tsx  PDF / LaTeX / ZIP download
│       │   ├── error-boundary.tsx   React error boundary with retry
│       │   └── __tests__/          Component tests
│       ├── __tests__/               Vitest setup (jest-dom, cleanup)
│       └── lib/
│           ├── api.ts               API client (FormData, timeout, abort)
│           ├── types.ts             TypeScript interfaces
│           └── utils.ts             cn(), formatDuration(), category labels
│
├── .github/workflows/ci.yml  CI: backend tests + frontend tests + Docker build
├── Makefile                   install, test, test-cov, lint, dev-*, docker-build
├── docker-compose.yml         Run both services with one command
├── CONTRIBUTING.md            Development workflow, code style, PR guidelines
├── examples/
│   └── sample_resume.tex      Example .tex file for testing the pipeline
└── docs/                      Detailed documentation
    ├── architecture.md        System design, request lifecycle, module map
    ├── error-handling.md      Request ID middleware, exception handlers
    ├── resilience.md          Fallback prompts, LLM failover
    ├── security.md            CORS, rate limiting, headers, validation
    ├── deployment.md          Docker, CI/CD, health check, env vars
    ├── testing.md             Strategy, coverage, mocking patterns
    ├── prompts.md             Langfuse management, fallback prompts
    └── troubleshooting.md     CORS errors, missing pdflatex, common fixes
```

## Production Features

| Category | What's Implemented |
|----------|--------------------|
| **Error Handling** | Request ID middleware (8-char UUID per request), global exception handlers, structured error responses with `request_id`, no stack trace leakage |
| **Observability** | Structured JSON + colored console logging with request_id, Langfuse LLM tracing, health check with version + uptime |
| **Resilience** | Embedded fallback prompts when Langfuse is down, OpenAI → Gemini LLM failover, graceful PDF compilation failure |
| **Security** | CORS with explicit headers (`Content-Type`, `Authorization`, `X-Request-ID`), rate limiting (10 req/min per IP), content-type validation on uploads, input validation (size, encoding, length), frontend security headers (X-Frame-Options, X-Content-Type-Options, etc.) |
| **Deployment** | Docker for both services (backend: non-root + HEALTHCHECK, frontend: multi-stage standalone), docker-compose orchestration, separated prod/dev requirements |
| **CI/CD** | GitHub Actions: backend tests + coverage (70% min), frontend tests + lint + build, Docker build |
| **Testing** | 207 backend tests + 39 frontend tests (246 total), async mock patterns, coverage enforcement |
| **DevEx** | Self-documenting Makefile, centralized constants, Pydantic settings |

## Prerequisites

Before starting, make sure you have:

- [ ] **Python 3.11+** — `python --version`
- [ ] **Node.js 20+** — `node --version`
- [ ] **npm** — `npm --version` (comes with Node.js)
- [ ] **pdflatex** (optional) — `pdflatex --version` — needed for PDF generation. Without it, the API still returns keyword analysis, match score, reorder plan, and diff — just no PDF. See [backend/README.md](backend/README.md#why-pdflatex) for install instructions.
- [ ] **OpenAI API key** — the only required secret. Get one at [platform.openai.com](https://platform.openai.com)

## Environment Variables

All env vars are configured in `backend/.env`. Only `OPENAI_API_KEY` is required.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key (GPT-4o-mini) |
| `GOOGLE_AI_API_KEY` | No | — | Gemini fallback (if OpenAI fails 5 times) |
| `LANGFUSE_SECRET_KEY` | No | — | Langfuse secret key (prompt management + tracing) |
| `LANGFUSE_PUBLIC_KEY` | No | — | Langfuse public key |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Langfuse host URL |
| `LLM_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `ALLOWED_ORIGINS` | No | `localhost:3000,3001` | CORS origins (comma-separated) |
| `BASE_TEX_PATH` | No | `resume_base.tex` | Path to the base LaTeX template file |
| `OUTPUT_DIR` | No | `output` | Directory for compiled PDF and LaTeX output |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `RATE_LIMIT_PER_MINUTE` | No | `10` | API rate limit per IP |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8001` | Frontend → backend URL (frontend `.env.local`) |

## Quick Start

```bash
# Using Makefile (recommended)
make install       # Install backend + frontend deps
make dev-backend   # Terminal 1: Backend on port 8001
make dev-frontend  # Terminal 2: Frontend on port 3001

# Or manually:
cd backend && pip install -r requirements-dev.txt
cp .env.example .env          # add your OPENAI_API_KEY (only required key)
uvicorn app.main:app --port 8001

cd frontend && npm install
npm run dev -- -p 3001
```

Open http://localhost:3001 — upload a .tex resume, paste a JD, click Tailor Resume.

> **Don't have a .tex resume?** Use the example file at [examples/sample_resume.tex](examples/sample_resume.tex) to test the pipeline.

### Docker Compose (alternative)

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Start both services
docker compose up --build

# Backend: http://localhost:8001, Frontend: http://localhost:3000
```

### Verify It's Working

```bash
# 1. Backend health check (should return {"status": "ok", ...})
curl http://localhost:8001/api/health

# 2. Frontend loads (should return HTML)
curl -s http://localhost:3001 | head -5

# 3. Test the full pipeline (optional — needs a .tex file)
curl -X POST http://localhost:8001/api/tailor \
  -F "resume_file=@your_resume.tex" \
  -F "jd_text=We are looking for a Backend Developer with Python, Django, REST APIs..."
```

If the health check returns `{"status": "ok"}`, both services are running correctly.

## Health Check

```bash
curl http://localhost:8001/api/health
```

```json
{
  "status": "ok",
  "service": "resume-tailor",
  "version": "1.0.0",
  "uptime_seconds": 42
}
```

Response headers include `X-Request-ID` on every request (e.g., `X-Request-ID: b4de6ae7`).

## Testing

```bash
make test           # Run all tests (backend + frontend)
make test-cov       # Backend tests with coverage report

# Or directly:
cd backend && pytest -q                                    # 207 tests
cd backend && pytest --cov=app --cov-report=term-missing   # with coverage
cd frontend && npx vitest run                              # 39 tests
```

## Prompt Management

All LLM prompts are managed in [Langfuse](https://cloud.langfuse.com) with embedded fallback prompts for resilience.

| Prompt Name | Purpose | Fallback? |
|-------------|---------|-----------|
| `resume-tailor-analyze` | Insert markers + extract skills from .tex | Yes |
| `resume-tailor-extract` | Extract JD keywords into categories | Yes |
| `resume-tailor-match` | Semantic matching of JD vs resume skills | Yes |

When Langfuse is unavailable, the pipeline continues using embedded fallback prompts (see [docs/resilience.md](docs/resilience.md)).

Push/update prompts:
```bash
cd backend && python scripts/push_prompts.py
```

## Documentation

Detailed documentation is in the [docs/](docs/) directory:

- [Architecture](docs/architecture.md) — System design, request lifecycle, module map
- [Error Handling](docs/error-handling.md) — Request ID, exception handlers, error format
- [Resilience](docs/resilience.md) — Fallback prompts, LLM failover, degradation
- [Security](docs/security.md) — CORS, rate limiting, headers, validation, Docker
- [Deployment](docs/deployment.md) — Docker, CI/CD, health check, environment variables
- [Testing](docs/testing.md) — Strategy, coverage, mocking patterns
- [Prompts](docs/prompts.md) — Langfuse management, fallback prompts
- [Troubleshooting](docs/troubleshooting.md) — CORS errors, missing pdflatex, Langfuse down, common fixes
- [Contributing](CONTRIBUTING.md) — Development workflow, code style, PR guidelines

## What Changes Per JD

| Element | How | Example |
|---------|-----|---------|
| Skills category order | Reorder by JD match count | Backend JD → backend line moves to top |
| Skills injection | Add matched keywords not already on resume | "REST APIs" added to backend line |
| Project order | Reorder by keyword overlap with JD | Backend JD → Django project moves up |
| Summary first line | Generate from role title + top matched skills | "Backend Developer with expertise in Django, FastAPI" |
| Experience emphasis | Highlight relevant keywords per entry | Zelthy entry → "Django, PostgreSQL" emphasized |

**What never changes:** Experience bullets, company names, dates, achievements, project descriptions, LaTeX layout.

## LaTeX Marker System

Step 0 (resume analyzer) inserts these comment markers into uploaded .tex files:

```latex
% SUMMARY_START
AI/LLM Engineer and Full-Stack Developer with...
% SUMMARY_END

% SKILLS_START
% SKILL_CAT:languages
\skillline{Languages}{Python, JavaScript, TypeScript} \\
% SKILL_CAT:backend
\skillline{Backend}{Django, FastAPI, Node.js} \\
% SKILLS_END

% PROJECTS_START
% PROJECT:chat_app
\projectentry{Real-Time Chat Room}{...}
% PROJECT:rag_engine
\projectentry{Hybrid Search RAG Engine}{...}
% PROJECTS_END

% EXPERIENCE_START
% EXP:zelthy
\experienceentry{Software Developer Intern}{Zelthy}{...}
% EXPERIENCE_END
```

Steps 3-4 use these markers to reorder and inject without touching any other LaTeX content.
