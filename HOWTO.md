# HOWTO — Using the Public Records Research app

A step-by-step guide to running and using the software. For architecture and deeper reference, see
[`README.md`](README.md) and the [`docs/`](docs/) folder.

> **Prefer the in-app guide?** After you sign in, open **User Guide** in the left navigation
> (http://localhost:3000/guide). It covers the same workflow with links straight into each screen.

> Reminder: this is a **research tool**. It suggests records that *might* be related and gives an
> explainable confidence score, but it **never confirms identity** — every match needs your review.

---

## 1. Start the app

Pick **one** of the two ways to run it.

### Option A — Local dev (fastest; SQLite, no Docker)

Backend (terminal 1):

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate   # first time only
pip install -e .                                        # first time only
python -m app.seed                                      # first time only: demo user + demo data
uvicorn app.main:app --reload                           # http://localhost:8000
```

Frontend (terminal 2):

```bash
cd frontend
npm install          # first time only
npm run dev          # http://localhost:3000
```

### Option B — Full stack (Docker: Postgres + Redis + worker)

```bash
cp .env.example .env      # set APP_SECRET_KEY (and OpenAI settings if you have them)
docker compose up --build
```

Migrations run and demo data is seeded automatically on first boot.

### Open it

| What          | URL                              |
| ------------- | -------------------------------- |
| **App (UI)**  | http://localhost:3000            |
| API docs      | http://localhost:8000/docs       |
| Health check  | http://localhost:8000/health     |

---

## 2. Log in

Use the seeded demo account:

```
Email:    demo@example.com
Password: demopassword123
```

Or click **Create one** on the login page to register your own account (this also creates your own
isolated workspace). After logging in you land on the **Dashboard**.

---

## 3. The dashboard

The Dashboard shows totals and things needing attention: total records and documents, records
imported this week, documents awaiting processing, **potential matches waiting for review**, reviewed
matches, failed ingestion jobs, and recent activity. Use the left-hand navigation to move between
sections.

---

## 4. Import data

Go to **Import Data**.

- **Fastest:** click **Import demo records** to load ~10 clearly-labeled synthetic records.
- **Upload your own:** choose a **PDF, CSV, TXT, or JSON** file, optionally fill in provenance
  (source name, original URL, jurisdiction, record type), then click **Upload & process**.
  - Files are validated by type/size and de-duplicated by SHA-256.
  - A `.csv` should have a header row; columns like `name, record_type, case_number, filing_date,
    jurisdiction, address, title, description, url` are mapped automatically. (See
    `sample_data/extra_records.csv` for a working example you can edit and upload.)
- **Adapters:** the page lists each available source adapter with its access method, terms,
  attribution, and rate limit.

Watch progress under **Processing Jobs** (status, errors, and retry). Scanned PDFs automatically get
OCR; text-based PDFs are read directly.

---

## 5. Search

Go to **Search**.

1. Type a query in **Query** (or leave it empty to list everything).
2. Pick a **Mode**:
   - **Keyword** / **Full-text** — general text search.
   - **Semantic** — meaning-based.
   - **Exact name** vs **Fuzzy name** — precise vs. spelling-tolerant.
   - **Address** / **Case number** — targeted lookups.
3. Optionally narrow with **Name, Address, Case #, Jurisdiction, Record type, State, Filed from/to**.
4. Click **Search**.

**Try it with the demo data:**

| Search        | Mode        | Shows                                                        |
| ------------- | ----------- | ----------------------------------------------------------- |
| `Rivera`      | Keyword     | The two linked Rivera filings + Rivera Holdings LLC.        |
| `David Thompson` vs `David Thomson` | Fuzzy vs Exact name | How near-duplicate names are (and aren't) matched. |
| `Margaret Chen` | Keyword   | Same name, two different addresses.                         |
| `2023-CV-004821` | Case number | The two records sharing that case.                       |

**Save a search:** type a name in the **"Save search as…"** box and click **Save search**.

---

## 6. Open a record

Click any result to open its detail page: title, type, source with the **original source link**,
jurisdiction, key dates, extracted entities, document text with **page references**, potential
matches, notes, and its review/audit history. You can **add notes** or **remove** the record here.

---

## 7. Find & review potential matches

Go to **Potential Matches**.

1. Click **Generate candidates** — the engine blocks, scores, and lists pairs that *might* refer to
   the same person/org/address/case.
2. Each row shows an **explainable confidence score (0–100)** and a category
   (Unlikely / Possible / Probable / Strong candidate) — this is **review guidance, not a
   determination**.
3. Click **Review** to open the **side-by-side** comparison: matching vs. differing fields, source
   links, dates, the rationale, and supporting / conflicting evidence plus any missing information.
4. Add reviewer notes and choose one:
   - **Confirm for project**, **Reject**, **Needs more info**, or **Duplicate**.

Nothing is ever merged automatically — confirming only records a relationship for your research.

---

## 8. Build a research project & generate a report

Go to **Research Projects**.

1. **Create** a project (name + objective).
2. Open it, use the **Add records** search box to find records, tick the ones you want, and click
   **Add … selected**.
3. Click **Generate report** to produce a **cited** research summary: sources/documents reviewed,
   key entities and dates, potentially related records with confidence and rationale, conflicting
   evidence, human-review status, reviewer notes, and links back to records. Claims are tied to
   `[record: <id>]` citations.
4. The report is labeled **AI-assisted** (if an AI model is configured) or **Deterministic
   template**. **Export** it as **Markdown, JSON, CSV, or printable HTML**.

---

## 9. Re-run saved searches

Go to **Saved Searches** to **Run** a saved query again. You'll see its last run time, result count,
and **what's new or removed since the last run**. Delete searches you no longer need.

---

## 10. Audit history & settings

- **Audit History** — every import, search, AI operation, review, and match decision is logged.
- **Settings** — app info and the full **compliance / responsible-use notice**.

---

## 11. (Optional) Enable AI — preferred: from the UI

By default the app runs in **deterministic mode** (no key needed). For deployments, configure the
LLM **in the app** (no server restart required for workspace keys):

1. Sign in → **Settings → AI / LLM**.
2. Paste your **API key**, optional **Base URL** (OpenAI-compatible, usually ends in `/v1`), and
   **model** name.
3. Click **Save AI settings**, then **Test connection**.
4. Open **AI Chat** in the left nav and send a short message to confirm the model replies.

Keys are stored **encrypted per workspace** and never returned in full by the API (only a short
hint). Reports and match explanations use this workspace config.

### Fallback: environment variables

You can still set env vars (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`) in `backend/.env`
or Docker `.env`. Environment is used only when the workspace has no saved key.

---

## 12. Run the tests (optional)

```bash
cd backend && pytest -q          # backend (SQLite, mocked AI)
cd frontend && npm test          # frontend (Vitest)
# In Docker:
docker compose exec backend pytest
docker compose exec frontend npm test
```

---

## Troubleshooting

- **Search shows nothing** — click **Search** (empty query lists all), or import data first
  (section 4). A brand-new account starts with an empty workspace.
- **Port already in use** — stop stray dev servers: `lsof -ti:8000,3000 | xargs kill`.
- **`ai_enabled: false` but I set a key** — make sure the env file is where the process runs
  (`backend/.env` for local `uvicorn`), then restart the backend.
- **AI calls fail / fall back to template** — check `OPENAI_BASE_URL` points at the API (not the web
  UI) and that `OPENAI_MODEL` matches a model the endpoint actually serves.
- **Want a clean slate (local)** — delete `backend/records.db` and re-run `python -m app.seed`.
