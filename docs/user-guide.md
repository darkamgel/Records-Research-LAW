# User guide

An end-to-end walkthrough of the Public Records Research platform. This tool helps you gather,
search, and compare **public** records — it never confirms an identity, and every potential match
requires your review.

> The same guide is available **inside the app** after login: open **User Guide** in the left
> navigation, or go to `/guide`. That page includes how to run the software locally and clickable
> links into Search, Import, Matches, and Projects. See also [`HOWTO.md`](../HOWTO.md).

## 1. Sign in

1. Start the stack (`docker compose up --build`) and open http://localhost:3000.
2. Register a new account, or use the seeded demo account:
   - **Email:** `demo@example.com`
   - **Password:** `demopassword123`
3. You land on the **Dashboard**, which shows totals (records, documents), items awaiting processing,
   matches awaiting review, reviewed matches, failed jobs, and recent activity.

The left navigation covers: Dashboard, Search, Records, Documents, Potential Matches, Research
Projects, Saved Searches, Import Data, Processing Jobs, Audit History, User Guide, Settings.

## 2. Import data

Go to **Import Data**.

- **Demonstration data** — click **Import demo records** to load clearly-labeled synthetic records
  (court filings, probate notices, public notices, property/organization filings), including
  intentional strong matches, uncertain matches, similar-but-different people, conflicting addresses,
  and incomplete dates.
- **Upload a file** — choose a **PDF, CSV, TXT, or JSON** file. Optionally add provenance (source
  name, original URL, jurisdiction, record type). Files are validated by type/size and de-duplicated
  by SHA-256, then processed in the background.
- **Source adapters** — the page lists each available adapter with its access method, terms,
  attribution, and rate limit.

Track progress under **Processing Jobs** (upload status, errors, retry).

## 3. How documents are processed

Uploaded PDFs are run through the pipeline: embedded text is extracted first; **OCR runs only if**
the text quality is poor (scanned/image PDFs). Text is chunked with page numbers and character
offsets preserved, entities are extracted (people, organizations, dates, addresses, cities/counties/
states/ZIPs, case/filing/parcel numbers, agencies, document type, jurisdiction), and values are
normalized while the originals are preserved. Results appear under **Documents** and as **Records**.

## 4. Search

Go to **Search**. Enter a query and pick a mode:

- **Keyword** / **Full-text** — general text search.
- **Semantic** — meaning-based (uses embeddings).
- **Exact name** / **Fuzzy name** — precise vs. tolerant name matching.
- **Address** / **Case number** — targeted lookups.

Refine with filters: jurisdiction, source, record type, date range, and review status. Results appear
in a table with source links; you can export results to CSV. Save the current query with the
**"Save search as…"** box.

## 5. Record detail

Click a record to see its title, type, source and **original source link**, jurisdiction, important
dates, extracted entities, document text with **page references**, potential matches, notes, and its
review/audit history. Add notes inline. You can remove a record from your workspace here.

## 6. Potential matches (human review)

Go to **Potential Matches** and click **Generate candidates**. The engine uses blocking + deterministic
features to propose pairs, each with an explainable **confidence score (0–100)** and category
(Unlikely / Possible / Probable / Strong candidate) — these are **review guidance, not identity
confirmations**.

Click **Review** on a candidate to open the side-by-side view showing matching fields, differing
fields, source links, dates, the confidence score, the rationale, and supporting/conflicting
evidence plus any missing information. Add reviewer notes and choose:

- **Confirm for project**, **Reject**, **Needs more info**, or **Duplicate**.

Records are **never merged automatically**; confirming records a relationship for your research only.

## 7. Research projects & reports

Go to **Research Projects**, create a project (name + objective), then:

1. Search and **add records** to the project.
2. Click **Generate report** to produce a cited research summary. It lists sources/documents
   reviewed, key entities and dates, potentially related records with confidence and rationale,
   conflicting evidence, human-review status, reviewer notes, and links back to records. Claims are
   tied to `[record: <id>]` citations.
3. The report is labeled **AI-assisted** (if an OpenAI key is configured) or **Deterministic
   template**. Export as **Markdown, JSON, CSV, or printable HTML**.

## 8. Saved searches

Go to **Saved Searches** to re-run a saved query, see its last run time and result count, and view
**what's new or removed since the last run**. Delete searches you no longer need.

## 9. Audit history & settings

- **Audit History** — a log of imports, searches, AI operations, reviews, and match decisions.
- **Settings** — application info and the full **compliance notice**.

## Working without an OpenAI key

Everything above works with **no** API key. Search, imports, extraction, and matching are fully
functional; AI summaries and match explanations fall back to a clearly-labeled deterministic
template, and embeddings use a local deterministic method. Add `OPENAI_API_KEY` to enable
LLM-assisted explanations and summaries.

## Responsible use

Use only public or user-uploaded data; respect source terms. Do not use this tool to make legal,
employment, housing, credit, insurance, immigration, educational, or law-enforcement decisions, to
infer protected characteristics, or to treat any suggested match as a confirmed identity. See the
[compliance notice](../README.md#compliance-and-responsible-use-notice).
