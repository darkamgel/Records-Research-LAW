"""LangGraph workflows.

Three graphs are defined:
- Workflow A: document processing summary.
- Workflow B: match analysis (deterministic score + optional LLM explanation).
- Workflow C: research summary generation.

The LLM never controls numeric scores. All LLM output is schema-validated. When
no API key is configured, every workflow falls back to a deterministic template.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.ai.client import AIClient, get_ai_client
from app.ai.prompts import (
    MATCH_EXPLAIN_SYSTEM,
    SUMMARY_SYSTEM,
    wrap_untrusted,
)
from app.ai.schemas import LLMMatchExplanation, LLMSummary, safe_validate
from app.entity_resolution.features import compute_features
from app.entity_resolution.scoring import score_pair


# --------------------------------------------------------------------------- #
# Workflow B: Match analysis
# --------------------------------------------------------------------------- #
class MatchState(TypedDict, total=False):
    record_a: Any
    record_b: Any
    use_ai: bool
    ai: Any
    features: list
    score: dict
    rationale: str
    rationale_source: str


def _b_features(state: MatchState) -> MatchState:
    state["features"] = compute_features(state["record_a"], state["record_b"])
    return state


def _b_score(state: MatchState) -> MatchState:
    result = score_pair(state["features"])
    state["score"] = {
        "confidence": result.confidence,
        "category": result.category,
        "feature_scores": result.feature_scores,
        "supporting": result.supporting,
        "conflicting": result.conflicting,
        "missing": result.missing,
        "rationale": result.rationale,
    }
    state["rationale"] = result.rationale
    state["rationale_source"] = "deterministic"
    return state


def _b_explain(state: MatchState) -> MatchState:
    if not state.get("use_ai"):
        return state
    ai: AIClient = state.get("ai") or get_ai_client()
    if not ai.enabled:
        return state
    score = state["score"]
    payload = (
        f"Feature scores: {score['feature_scores']}\n"
        f"Supporting: {[s['detail'] for s in score['supporting']]}\n"
        f"Conflicting: {[c['detail'] for c in score['conflicting']]}\n"
        f"Missing: {score['missing']}\n"
        f"Deterministic confidence: {score['confidence']} ({score['category']})"
    )
    raw = ai.structured_json(MATCH_EXPLAIN_SYSTEM, wrap_untrusted("MATCH FEATURES", payload), max_tokens=250)
    validated = safe_validate(LLMMatchExplanation, raw)
    if validated:
        # Prepend deterministic disclaimer; never let the LLM change the score.
        state["rationale"] = (
            f"[AI-assisted explanation] {validated.rationale} "
            f"(Deterministic score {score['confidence']:.0f}/100 — review guidance only.)"
        )
        state["rationale_source"] = "ai"
    return state


def build_match_graph():
    g = StateGraph(MatchState)
    g.add_node("features", _b_features)
    g.add_node("score", _b_score)
    g.add_node("explain", _b_explain)
    g.set_entry_point("features")
    g.add_edge("features", "score")
    g.add_edge("score", "explain")
    g.add_edge("explain", END)
    return g.compile()


_match_graph = None


def analyze_match(
    record_a, record_b, *, use_ai: bool = False, ai: AIClient | None = None
) -> dict:
    global _match_graph
    if _match_graph is None:
        _match_graph = build_match_graph()
    out = _match_graph.invoke(
        {
            "record_a": record_a,
            "record_b": record_b,
            "use_ai": use_ai,
            "ai": ai or get_ai_client(),
        }
    )
    return {"score": out["score"], "rationale": out["rationale"],
            "rationale_source": out["rationale_source"]}


# --------------------------------------------------------------------------- #
# Workflow C: Research summary
# --------------------------------------------------------------------------- #
class SummaryState(TypedDict, total=False):
    project_name: str
    objective: str
    records: list
    confirmed: list
    unreviewed: list
    use_ai: bool
    ai: Any
    summary_markdown: str
    cited_ids: list
    ai_generated: bool


def _c_collect(state: SummaryState) -> SummaryState:
    return state


def _c_generate(state: SummaryState) -> SummaryState:
    ai: AIClient = state.get("ai") or get_ai_client()
    records = state["records"]
    if state.get("use_ai") and ai.enabled:
        lines = []
        for r in records:
            lines.append(
                f"[record: {r['id']}] type={r.get('record_type')} name={r.get('primary_name')} "
                f"case={r.get('case_number')} date={r.get('filing_date')} "
                f"jurisdiction={r.get('jurisdiction')} url={r.get('original_url')} "
                f"title={r.get('title')}"
            )
        user = (
            f"Project: {state.get('project_name')}\nObjective: {state.get('objective')}\n"
            f"User-confirmed relationships: {state.get('confirmed')}\n"
            f"Unreviewed potential relationships: {state.get('unreviewed')}\n\n"
            + wrap_untrusted("RECORDS", "\n".join(lines))
        )
        raw = ai.structured_json(SUMMARY_SYSTEM, user, max_tokens=1200)
        validated = safe_validate(LLMSummary, raw)
        if validated:
            valid_ids = {str(r["id"]) for r in records}
            cited = [cid for cid in validated.cited_record_ids if cid in valid_ids]
            state["summary_markdown"] = validated.summary_markdown
            state["cited_ids"] = cited
            state["ai_generated"] = True
            return state
    # Deterministic template fallback.
    state["summary_markdown"] = _template_summary(state)
    state["cited_ids"] = [str(r["id"]) for r in records]
    state["ai_generated"] = False
    return state


def _template_summary(state: SummaryState) -> str:
    records = state["records"]
    lines = [
        f"# Research Summary: {state.get('project_name', 'Untitled')}",
        "",
        f"**Objective:** {state.get('objective') or 'N/A'}",
        "",
        "> AI-assisted summaries are disabled (no API key) or unavailable. This is a "
        "deterministic template summary. It is research guidance only and is NOT an "
        "identity determination. All potential relationships require human review.",
        "",
        f"## Records Reviewed ({len(records)})",
    ]
    for r in records:
        lines.append(
            f"- **{r.get('title') or r.get('primary_name') or 'Record'}** "
            f"({r.get('record_type') or 'record'}) — "
            f"case {r.get('case_number') or 'N/A'}, filed {r.get('filing_date') or 'N/A'}, "
            f"{r.get('jurisdiction') or 'N/A'}. [record: {r['id']}]"
            + (f" [source]({r['original_url']})" if r.get("original_url") else "")
        )
    if state.get("confirmed"):
        lines += ["", "## User-Confirmed Relationships"]
        for c in state["confirmed"]:
            lines.append(f"- {c} (confirmed by reviewer)")
    if state.get("unreviewed"):
        lines += ["", "## Unreviewed Potential Relationships (require human review)"]
        for u in state["unreviewed"]:
            lines.append(f"- {u}")
    lines += ["", "---", "_AI-use disclaimer: content is AI-assisted/deterministic research "
              "guidance, not a legal or identity determination._"]
    return "\n".join(lines)


def build_summary_graph():
    g = StateGraph(SummaryState)
    g.add_node("collect", _c_collect)
    g.add_node("generate", _c_generate)
    g.set_entry_point("collect")
    g.add_edge("collect", "generate")
    g.add_edge("generate", END)
    return g.compile()


_summary_graph = None


def generate_summary(state: dict, *, ai: AIClient | None = None) -> dict:
    global _summary_graph
    if _summary_graph is None:
        _summary_graph = build_summary_graph()
    payload = dict(state)
    if ai is not None:
        payload["ai"] = ai
    elif "ai" not in payload:
        payload["ai"] = get_ai_client()
    return _summary_graph.invoke(payload)


# --------------------------------------------------------------------------- #
# Workflow A: Document processing summary
# --------------------------------------------------------------------------- #
class DocState(TypedDict, total=False):
    page_count: int
    char_count: int
    ocr_used: bool
    entity_count: int
    warnings: list
    summary: str


def _a_summary(state: DocState) -> DocState:
    state["summary"] = (
        f"Processed {state.get('page_count', 0)} page(s), "
        f"{state.get('char_count', 0)} characters, "
        f"{'OCR used' if state.get('ocr_used') else 'no OCR'}, "
        f"{state.get('entity_count', 0)} entities extracted."
    )
    return state


def build_doc_graph():
    g = StateGraph(DocState)
    g.add_node("summary", _a_summary)
    g.set_entry_point("summary")
    g.add_edge("summary", END)
    return g.compile()


_doc_graph = None


def document_processing_summary(state: dict) -> dict:
    global _doc_graph
    if _doc_graph is None:
        _doc_graph = build_doc_graph()
    return _doc_graph.invoke(state)
