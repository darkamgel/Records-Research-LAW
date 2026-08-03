# Entity resolution & matching

The matching engine identifies records that **may** refer to the same person, organization, address,
case, property, or event. It is **explainable and deterministic**: an LLM may *explain* evidence, but
the numeric confidence score is computed entirely by application logic. Scores and categories are
**review guidance, not identity confirmation**, and records are **never merged automatically**.

Pipeline: **blocking → feature computation → weighted scoring → evidence & rationale → human review**.
Code lives in `app/entity_resolution/`.

## 1. Blocking (candidate generation)

Comparing every record to every other record is O(n²). `blocking.py` generates a much smaller set of
candidate pairs using blocking keys such as:

- Same normalized last name + state
- Same ZIP code + similar first name
- Same organization + city
- Same case / filing / parcel identifier
- Similar address with overlapping dates

Only records within the same block are compared, and only within the same workspace.

## 2. Features (`features.py`)

For each candidate pair, deterministic per-feature similarity scores (0–1) are computed and tagged as
`supporting`, `conflicting`, or neutral, each with a human-readable `detail`:

- `first_name`, `middle_name`, `last_name`, `full_name` — string/token/phonetic similarity.
- `address` — normalized address similarity.
- `geographic` — shared city/county/state/ZIP.
- `date` — date compatibility (exact, proximity, or contradiction).
- `organization` — normalized organization similarity.
- `identifier` — shared case/filing/parcel number (very strong signal).
- `semantic` — embedding cosine similarity when useful.
- `source_reliability` — small tie-breaker, not a base feature.

Missing inputs yield a `None` score for that feature (recorded as *missing information*) rather than
a penalty.

## 3. Weighted score (`scoring.py` + `config.py`)

The confidence score is a weight-normalized average of the features that could actually be computed,
scaled to 0–100, with a capped penalty for contradictions. Because it normalizes over *available*
features, missing data lowers coverage instead of silently deflating the score.

Default weights (`config.py`, fully configurable):

| Feature              | Weight |
| -------------------- | ------ |
| `identifier`         | 4.0    |
| `last_name`          | 3.0    |
| `full_name`          | 2.5    |
| `address`            | 2.5    |
| `first_name`         | 2.0    |
| `organization`       | 2.0    |
| `geographic`         | 1.5    |
| `date`               | 1.0    |
| `semantic`           | 1.0    |
| `middle_name`        | 0.5    |
| `source_reliability` | 0.5 (tie-breaker) |

```text
base       = (Σ score_i · weight_i) / (Σ weight_i) · 100      # over available features
penalty    = min(15, num_contradictions · 7.5)
confidence = clamp(base − penalty, 0, 100)
```

### Categories (review guidance only)

| Score  | Category         |
| ------ | ---------------- |
| 85–100 | Strong candidate |
| 65–84  | Probable         |
| 40–64  | Possible         |
| 0–39   | Unlikely         |

## 4. Evidence & rationale

`score_pair` returns the overall confidence, category, per-feature scores, supporting evidence,
conflicting evidence, missing information, and a plain-language rationale that always states the
result is *review guidance, not an identity determination*. This maps directly to the review UI and
to `match_evidence` rows.

## 5. AI explanation (optional, non-authoritative)

If an OpenAI key is configured, Workflow B (`app/ai/workflows.py`) can ask the model to *explain* the
already-computed evidence in prose. The explanation is schema-validated and clearly labeled as
AI-assisted. **The LLM never changes the numeric score.** With no key, the deterministic rationale is
used.

## 6. Human review

Every candidate is persisted with `review_status = not_reviewed` and sent to the review queue. In the
**Potential Matches** UI a reviewer sees the two records side by side — matching fields, differing
fields, source links, dates, confidence, rationale, supporting/conflicting evidence — and records a
decision:

- **Confirmed for this research project**
- **Rejected**
- **Needs more information**
- **Duplicate**
- **Not reviewed** (default)

Decisions and reviewer notes are written to `review_decisions` and the audit log. Confirming a match
records a relationship for the project; it does **not** merge the underlying records.

## Tuning

Adjust `DEFAULT_WEIGHTS`, `CATEGORY_THRESHOLDS`, and `CONTRADICTION_PENALTY` in
`app/entity_resolution/config.py`. Because scoring is deterministic, changes are predictable and
covered by `backend/app/tests/test_matching.py`.
