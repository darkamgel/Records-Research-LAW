# AI workflows

AI orchestration uses **LangGraph** `StateGraph`s (`app/ai/workflows.py`) with the OpenAI SDK behind
a thin client (`app/ai/client.py`). Three principles hold throughout:

1. **The LLM never controls numeric scores.** Confidence is always computed by deterministic
   application logic; the LLM only *explains*.
2. **All model output is schema-validated** with Pydantic (`app/ai/schemas.py`) before use;
   invalid output is discarded and the deterministic path is used.
3. **Graceful no-key mode.** With no `OPENAI_API_KEY`, every workflow falls back to a deterministic
   template, and embeddings use a local hashing fallback. Imports, search, extraction, and matching
   all keep working.

## The AI client (`app/ai/client.py`)

- `enabled` — `True` only when an API key is configured.
- `structured_json(system, user, max_tokens)` — chat completion requesting JSON, with retry, token
  limits, and timeout handling.
- `embed(texts)` — real embeddings when enabled; otherwise a deterministic 1536-dim hash embedding
  (matches the `pgvector` dimension) so semantic features remain reproducible offline.

## Prompt-injection defense (`app/ai/prompts.py`)

Imported documents are **untrusted input**. System instructions are kept separate from document
content, and all untrusted text is wrapped with `wrap_untrusted(label, text)` which fences the
content and instructs the model to treat it as data only — never as instructions, never as a request
for secrets or tool calls. Known injection patterns (e.g. "ignore previous instructions") are
detected and neutralized/flagged.

## Workflow A — Document processing

Orchestrates the ingestion pipeline and produces a processing summary:

1. Validate input → 2. Extract embedded text → 3. Run OCR **only if** quality is poor →
4. Chunk (preserve page numbers + character offsets) → 5. Extract entities (regex → address parsing
→ optional spaCy → optional schema-validated LLM) → 6. Validate structured output → 7. Normalize →
8. Store results → 9. Create embeddings → 10. Emit a processing summary
(`document_processing_summary`) with page/char counts, OCR-used flag, entity count, and warnings.

## Workflow B — Match analysis

`analyze_match(record_a, record_b, use_ai=False)` runs a graph: `features → score → explain`.

- **features** — `compute_features` (deterministic per-feature similarity, `app/entity_resolution`).
- **score** — `score_pair` produces the confidence, category, supporting/conflicting evidence,
  missing info, and a deterministic rationale (`rationale_source = "deterministic"`).
- **explain** — *only* if `use_ai` and the client is enabled: the model is asked to explain the
  already-computed evidence. The response is validated (`LLMMatchExplanation`); on success the
  rationale is replaced with an AI-labeled explanation that still cites the deterministic score, and
  `rationale_source = "ai"`. **The score is never altered.**

## Workflow C — Research summary

`generate_summary(state)` runs `collect → generate`:

- **collect** — gathers selected records, provenance, key entities, and separates
  **user-confirmed** relationships from **unreviewed** potential ones.
- **generate** — if `use_ai` and enabled, the model drafts a Markdown summary and returns
  `cited_record_ids`; citations are validated against the actual record id set (hallucinated ids are
  dropped) and `ai_generated = True`. Otherwise a **deterministic template** summary
  (`_template_summary`) is produced with `ai_generated = False`.

Both paths always include an AI-use disclaimer, clearly distinguish confirmed vs. unreviewed
relationships, and tie claims back to `[record: <id>]` citations with source links.

## Reports

`app/services/report_service.py` wraps Workflow C, persists the result to `generated_reports`, and
supports export as Markdown, JSON, CSV, and printable HTML. Reports display an AI-assisted vs.
deterministic-template badge in the UI.

## Reliability controls

- Retry handling and timeouts on model calls.
- Token limits (`max_tokens`) per workflow.
- Strict Pydantic validation (`safe_validate`) — invalid output → deterministic fallback.
- Citation validation against known record ids.

## Testing without a key

`backend/app/tests/test_reports_ai.py` and `test_security_adapters.py` mock the client to return
canned, schema-valid JSON, and also exercise the deterministic fallback. The whole suite runs with no
network and no API key.
