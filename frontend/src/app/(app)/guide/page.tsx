"use client";

import Link from "next/link";

const TOC = [
  { id: "start", label: "1. Start here" },
  { id: "login", label: "2. Sign in" },
  { id: "import", label: "3. Import records" },
  { id: "search", label: "4. Search" },
  { id: "record", label: "5. Open a record" },
  { id: "matches", label: "6. Review matches" },
  { id: "projects", label: "7. Projects & reports" },
  { id: "saved", label: "8. Saved searches" },
  { id: "audit", label: "9. Audit & settings" },
  { id: "ai", label: "Enable LLM (UI)" },
  { id: "run-local", label: "How to run locally" },
  { id: "try", label: "Try these searches" },
  { id: "tips", label: "Common questions" },
];

export default function GuidePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">User guide</h1>
        <p className="text-sm text-gray-500 mt-1 max-w-2xl">
          How to run and use this app as a researcher. Work through the steps below in order the
          first time — you can jump back anytime from the left navigation.
        </p>
      </div>

      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        This is a <strong>research tool</strong>, not an identity service. Match scores are review
        guidance only. Nothing is ever confirmed or merged automatically — you decide.
      </div>

      <div className="lg:grid lg:grid-cols-[220px_1fr] lg:gap-8">
        <aside className="mb-6 lg:mb-0">
          <div className="card p-3 lg:sticky lg:top-4">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide px-2 mb-2">
              On this page
            </div>
            <nav className="space-y-0.5">
              {TOC.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </div>
        </aside>

        <div className="space-y-8">
          <Section id="start" title="1. Start here">
            <p>
              After you sign in you land on the{" "}
              <PageLink href="/dashboard">Dashboard</PageLink>. It shows totals (records,
              documents), items waiting for processing or review, failed jobs, and recent activity.
              Use the left sidebar to move between sections.
            </p>
            <ol className="list-decimal pl-5 space-y-1 mt-3 text-sm text-gray-700">
              <li>Import or load demo data</li>
              <li>Search and open records</li>
              <li>Generate and review potential matches</li>
              <li>Build a research project and export a report</li>
            </ol>
          </Section>

          <Section id="login" title="2. Sign in">
            <p>Use the seeded demo account (after the app has been started and seeded):</p>
            <div className="mt-3 rounded-md bg-gray-50 border border-gray-200 px-3 py-2 font-mono text-sm">
              Email: demo@example.com
              <br />
              Password: demopassword123
            </div>
            <p className="mt-3">
              Or register a new account from the login page — that creates your own isolated
              workspace. A brand-new workspace starts empty until you import data.
            </p>
          </Section>

          <Section id="import" title="3. Import records">
            <p>
              Go to <PageLink href="/import">Import Data</PageLink>.
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-3 text-sm text-gray-700">
              <li>
                <strong>Fastest:</strong> click <em>Import demo records</em> to load synthetic
                court, probate, property, and organization filings (clearly labeled as demo data).
              </li>
              <li>
                <strong>Upload your own:</strong> choose a PDF, CSV, TXT, or JSON file. Optionally
                fill source name, original URL, jurisdiction, and record type, then click{" "}
                <em>Upload &amp; process</em>.
              </li>
              <li>
                CSV tip: include a header row. Columns such as{" "}
                <code className="text-xs bg-gray-100 px-1 rounded">
                  name, record_type, case_number, filing_date, jurisdiction, address, title,
                  description, url
                </code>{" "}
                are mapped automatically.
              </li>
            </ul>
            <p className="mt-3">
              Watch status under <PageLink href="/jobs">Processing Jobs</PageLink>. Scanned PDFs
              use OCR when needed; text PDFs are read directly. Duplicates are detected by SHA-256.
            </p>
          </Section>

          <Section id="search" title="4. Search">
            <p>
              Go to <PageLink href="/search">Search</PageLink>.
            </p>
            <ol className="list-decimal pl-5 space-y-1 mt-3 text-sm text-gray-700">
              <li>
                Type a query — or leave it empty and click <em>Search</em> to list everything.
              </li>
              <li>
                Pick a mode: Keyword, Full-text, Semantic, Exact name, Fuzzy name, Address, or Case
                number.
              </li>
              <li>
                Optionally narrow with Name, Address, Case #, Jurisdiction, Record type, State, and
                date range.
              </li>
              <li>
                Click <em>Search</em>. Save useful queries with <em>Save search as…</em>.
              </li>
            </ol>
          </Section>

          <Section id="record" title="5. Open a record">
            <p>
              From search results or <PageLink href="/records">Records</PageLink>, open any row.
              You&apos;ll see title, type, source link, jurisdiction, dates, extracted entities,
              document text with page references, potential matches, notes, and review history.
            </p>
            <p className="mt-2">
              Add notes for your research, or remove a record from your workspace if you no longer
              need it.
            </p>
          </Section>

          <Section id="matches" title="6. Review potential matches">
            <p>
              Go to <PageLink href="/matches">Potential Matches</PageLink>.
            </p>
            <ol className="list-decimal pl-5 space-y-1 mt-3 text-sm text-gray-700">
              <li>
                Click <em>Generate candidates</em> so the system proposes pairs that{" "}
                <em>might</em> refer to the same person, organization, address, or case.
              </li>
              <li>
                Each row has a confidence score (0–100) and category (Unlikely → Strong candidate).
                Treat these as review guidance only.
              </li>
              <li>
                Click <em>Review</em> for a side-by-side view: matching vs differing fields, source
                links, rationale, and supporting / conflicting evidence.
              </li>
              <li>
                Decide: Confirm for project, Reject, Needs more info, or Duplicate — and add
                reviewer notes.
              </li>
            </ol>
            <p className="mt-3 text-sm text-gray-600">
              Records are never merged automatically. Confirming only records a relationship for
              your research.
            </p>
          </Section>

          <Section id="projects" title="7. Research projects &amp; reports">
            <p>
              Go to <PageLink href="/projects">Research Projects</PageLink>.
            </p>
            <ol className="list-decimal pl-5 space-y-1 mt-3 text-sm text-gray-700">
              <li>Create a project with a name and objective.</li>
              <li>Open it, search for records, select them, and add them to the project.</li>
              <li>
                Click <em>Generate report</em> for a cited summary (sources, entities, dates,
                related records, review status, and links back to records).
              </li>
              <li>
                Export as Markdown, JSON, CSV, or printable HTML. Reports are labeled AI-assisted
                or deterministic template depending on configuration.
              </li>
            </ol>
          </Section>

          <Section id="saved" title="8. Saved searches">
            <p>
              On <PageLink href="/saved-searches">Saved Searches</PageLink>, re-run a saved query
              to see last-run time, result count, and what is new or removed since the previous run.
              Delete searches you no longer need.
            </p>
          </Section>

          <Section id="audit" title="9. Audit history &amp; settings">
            <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
              <li>
                <PageLink href="/audit">Audit History</PageLink> — imports, searches, AI
                operations, reviews, and match decisions.
              </li>
              <li>
                <PageLink href="/settings">Settings</PageLink> — account, workspace, AI mode
                (enabled vs deterministic), and the compliance notice.
              </li>
            </ul>
          </Section>

          <Section id="ai" title="Enable the LLM from the UI (for deployment)">
            <p>
              You do <strong>not</strong> need a server <code className="text-xs bg-gray-100 px-1 rounded">.env</code>{" "}
              key for day-to-day use after deploy. Open{" "}
              <PageLink href="/settings">Settings → AI / LLM</PageLink>, paste your API key,
              optional base URL (OpenAI-compatible, usually ends in{" "}
              <code className="text-xs bg-gray-100 px-1 rounded">/v1</code>), and model name. Save,
              click <em>Test connection</em>, then try{" "}
              <PageLink href="/chat">AI Chat</PageLink> — a small chatbot that confirms the model
              answers. Reports and match explanations then use that workspace config. Keys are
              stored encrypted and never shown in full again.
            </p>
          </Section>

          <Section id="run-local" title="How to run this software (operators)">
            <p className="mb-3">
              If you are setting up the app on your machine (not just using a running site), pick
              one option:
            </p>

            <div className="space-y-4">
              <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
                <h3 className="font-medium text-sm mb-2">Option A — Local (fastest)</h3>
                <p className="text-xs text-gray-500 mb-2">Two terminals. First time only steps marked.</p>
                <pre className="text-xs overflow-x-auto whitespace-pre-wrap font-mono text-gray-800 leading-relaxed">{`# Terminal 1 — backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate   # first time
pip install -e .                                        # first time
python -m app.seed                                      # first time
uvicorn app.main:app --reload                           # http://localhost:8000

# Terminal 2 — frontend
cd frontend
npm install                                             # first time
npm run dev                                             # http://localhost:3000`}</pre>
              </div>

              <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
                <h3 className="font-medium text-sm mb-2">Option B — Docker (full stack)</h3>
                <pre className="text-xs overflow-x-auto whitespace-pre-wrap font-mono text-gray-800 leading-relaxed">{`cp .env.example .env    # set APP_SECRET_KEY
docker compose up --build
# App: http://localhost:3000  ·  API docs: http://localhost:8000/docs`}</pre>
              </div>
            </div>

            <p className="mt-3 text-sm text-gray-600">
              Optional AI: set <code className="text-xs bg-gray-100 px-1 rounded">OPENAI_API_KEY</code>{" "}
              (and for a custom OpenAI-compatible server,{" "}
              <code className="text-xs bg-gray-100 px-1 rounded">OPENAI_BASE_URL</code> +{" "}
              <code className="text-xs bg-gray-100 px-1 rounded">OPENAI_MODEL</code>) in{" "}
              <code className="text-xs bg-gray-100 px-1 rounded">backend/.env</code> for local runs,
              then restart the backend. Without a key, imports, search, matching, and template
              reports still work.
            </p>
          </Section>

          <Section id="try" title="Try these searches (demo data)">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-3">Search</th>
                    <th className="py-2 pr-3">Mode</th>
                    <th className="py-2">What you should see</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700">
                  <Row q="Rivera" mode="Keyword" result="Linked Rivera filings + Rivera Holdings LLC" />
                  <Row
                    q="David Thompson / Thomson"
                    mode="Fuzzy vs Exact"
                    result="Near-duplicate names that are different people"
                  />
                  <Row q="Margaret Chen" mode="Keyword" result="Same name, different addresses" />
                  <Row q="2023-CV-004821" mode="Case number" result="Two records sharing that case" />
                  <Row q="Priya Nair" mode="Keyword" result="Extra CSV import (if you uploaded it)" />
                </tbody>
              </table>
            </div>
            <p className="mt-3">
              Then open <PageLink href="/matches">Potential Matches</PageLink> →{" "}
              <em>Generate candidates</em> to practice review.
            </p>
          </Section>

          <Section id="tips" title="Common questions">
            <dl className="space-y-3 text-sm">
              <Tip q="Search shows nothing.">
                Click <em>Search</em> with an empty query to list all records, or import data first.
                A new account starts with an empty workspace.
              </Tip>
              <Tip q="Is a high match score a confirmed identity?">
                No. Scores are review guidance only. Always open the side-by-side review and decide
                yourself.
              </Tip>
              <Tip q="Why does the report say “deterministic template”?">
                No OpenAI (or compatible) API key is configured. Everything else still works; AI
                prose is replaced by a structured template.
              </Tip>
              <Tip q="Where do I see upload errors?">
                Check <PageLink href="/jobs">Processing Jobs</PageLink> for status, errors, and
                retry.
              </Tip>
              <Tip q="Can I use real government sources?">
                Yes, via compliant adapters (official API, bulk download, RSS, or user upload). See
                Import Data for each adapter&apos;s terms and attribution. Do not scrape sources that
                prohibit automated access.
              </Tip>
            </dl>
          </Section>

          <div className="card p-4 flex flex-wrap gap-2 items-center justify-between">
            <p className="text-sm text-gray-600">Ready to try it?</p>
            <div className="flex flex-wrap gap-2">
              <Link href="/import" className="btn-primary">
                Import data
              </Link>
              <Link href="/search" className="btn-secondary">
                Open search
              </Link>
              <Link href="/dashboard" className="btn-secondary">
                Back to dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="card p-5 scroll-mt-4">
      <h2 className="text-base font-semibold mb-3">{title}</h2>
      <div className="text-sm text-gray-700 space-y-2">{children}</div>
    </section>
  );
}

function PageLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-brand-600 hover:underline font-medium">
      {children}
    </Link>
  );
}

function Row({ q, mode, result }: { q: string; mode: string; result: string }) {
  return (
    <tr className="border-b border-gray-100 align-top">
      <td className="py-2 pr-3 font-mono text-xs">{q}</td>
      <td className="py-2 pr-3 whitespace-nowrap">{mode}</td>
      <td className="py-2">{result}</td>
    </tr>
  );
}

function Tip({ q, children }: { q: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="font-medium text-gray-900">{q}</dt>
      <dd className="text-gray-600 mt-0.5">{children}</dd>
    </div>
  );
}
