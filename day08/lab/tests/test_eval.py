"""
test_eval.py — Property-based and unit tests for eval.py (Sprint 4)
====================================================================
Tests cover all 13 correctness properties from the design document.
LLM calls are always mocked — never call the real LLM in tests.
"""

import sys
import os
import json
import csv
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Add lab directory to path so we can import eval
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest.mock as mock

# Strategy helpers
def make_chunk(source="docs/test.txt", text="some content"):
    return {"metadata": {"source": source}, "text": text, "score": 0.9}

def make_question(qid="Q1", question="Test?", expected_answer="Answer.", expected_sources=None, category="test"):
    return {
        "id": qid,
        "question": question,
        "expected_answer": expected_answer,
        "expected_sources": expected_sources or [],
        "category": category,
    }

def make_result_row(qid="Q1", config_label="baseline"):
    return {
        "id": qid,
        "category": "test",
        "query": "Test question?",
        "answer": "Test answer.",
        "expected_answer": "Expected answer.",
        "faithfulness": 4,
        "faithfulness_notes": "Mostly grounded.",
        "relevance": 5,
        "relevance_notes": "Directly addresses.",
        "context_recall": 5,
        "context_recall_notes": "All sources found.",
        "completeness": 3,
        "completeness_notes": "Missing some points.",
        "config_label": config_label,
    }


# =============================================================================
# Import eval module with mocked dependencies
# =============================================================================

@pytest.fixture(autouse=True)
def mock_rag_answer_module():
    """Mock the rag_answer module so eval.py can be imported without real LLM."""
    mock_module = MagicMock()
    mock_module.call_llm = MagicMock(return_value='{"score": 4, "notes": "mocked"}')
    mock_module.rag_answer = MagicMock(return_value={
        "answer": "Mocked answer",
        "sources": ["docs/test.txt"],
        "chunks_used": [make_chunk()],
        "config": {},
    })
    with patch.dict("sys.modules", {"rag_answer": mock_module}):
        yield mock_module


def get_eval_module():
    """Import eval module fresh with mocked rag_answer."""
    import importlib
    if "eval" in sys.modules:
        del sys.modules["eval"]
    import eval as eval_mod
    return eval_mod


# =============================================================================
# UNIT TESTS — Checkpoint (Task 5)
# =============================================================================

class TestScoreFaithfulness:
    def test_empty_chunks_returns_score_1(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        result = eval_mod.score_faithfulness("some answer", [])
        assert result["score"] == 1
        assert "No context retrieved" in result["notes"]

    def test_with_chunks_calls_llm(self, mock_rag_answer_module):
        mock_rag_answer_module.call_llm.return_value = '{"score": 5, "notes": "fully grounded"}'
        eval_mod = get_eval_module()
        chunks = [make_chunk()]
        result = eval_mod.score_faithfulness("answer", chunks)
        assert result["score"] == 5

    def test_llm_parse_error_returns_none_score(self, mock_rag_answer_module):
        mock_rag_answer_module.call_llm.return_value = "not json at all"
        eval_mod = get_eval_module()
        chunks = [make_chunk()]
        result = eval_mod.score_faithfulness("answer", chunks)
        assert result["score"] is None
        assert "Parse error" in result["notes"]


class TestScoreAnswerRelevance:
    def test_returns_score_from_llm(self, mock_rag_answer_module):
        mock_rag_answer_module.call_llm.return_value = '{"score": 3, "notes": "partially relevant"}'
        eval_mod = get_eval_module()
        result = eval_mod.score_answer_relevance("What is X?", "X is Y.")
        assert result["score"] == 3

    def test_parse_error_returns_none(self, mock_rag_answer_module):
        mock_rag_answer_module.call_llm.return_value = "invalid"
        eval_mod = get_eval_module()
        result = eval_mod.score_answer_relevance("Q", "A")
        assert result["score"] is None


class TestScoreContextRecall:
    def test_empty_expected_sources(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        result = eval_mod.score_context_recall([], [])
        assert result["score"] is None
        assert result["recall"] is None

    def test_all_sources_found(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        chunks = [make_chunk(source="docs/policy_refund_v4.txt")]
        result = eval_mod.score_context_recall(chunks, ["policy_refund_v4.txt"])
        assert result["score"] == 5
        assert result["recall"] == 1.0

    def test_no_sources_found(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        chunks = [make_chunk(source="docs/other.txt")]
        result = eval_mod.score_context_recall(chunks, ["policy_refund_v4.txt"])
        assert result["recall"] == 0.0
        assert result["score"] == 0


class TestScoreCompleteness:
    def test_empty_expected_answer_returns_none(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        result = eval_mod.score_completeness("Q", "A", "")
        assert result["score"] is None
        assert result["missing_points"] == []
        assert "No expected answer" in result["notes"]

    def test_returns_score_and_missing_points(self, mock_rag_answer_module):
        mock_rag_answer_module.call_llm.return_value = '{"score": 3, "missing_points": ["point A"], "notes": "missing some"}'
        eval_mod = get_eval_module()
        result = eval_mod.score_completeness("Q", "A", "Expected A with point A.")
        assert result["score"] == 3
        assert "point A" in result["missing_points"]


class TestParseJudgeResponse:
    def test_valid_json_parsed(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        result = eval_mod._parse_judge_response('{"score": 4, "notes": "good"}')
        assert result["score"] == 4
        assert result["notes"] == "good"

    def test_invalid_json_returns_fallback(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        raw = "not json"
        result = eval_mod._parse_judge_response(raw)
        assert result["score"] is None
        assert f"Parse error: {raw}" == result["notes"]

    def test_score_out_of_range_returns_fallback(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        raw = '{"score": 6, "notes": "out of range"}'
        result = eval_mod._parse_judge_response(raw)
        assert result["score"] is None

    def test_missing_score_key_returns_fallback(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        raw = '{"notes": "no score here"}'
        result = eval_mod._parse_judge_response(raw)
        assert result["score"] is None

    def test_strips_markdown_fences(self, mock_rag_answer_module):
        eval_mod = get_eval_module()
        raw = '```json\n{"score": 3, "notes": "ok"}\n```'
        result = eval_mod._parse_judge_response(raw)
        assert result["score"] == 3


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

# Strategies
chunk_strategy = st.fixed_dictionaries({
    "metadata": st.fixed_dictionaries({"source": st.text(min_size=1, max_size=50)}),
    "text": st.text(min_size=1, max_size=200),
    "score": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
})

question_strategy = st.fixed_dictionaries({
    "id": st.text(min_size=1, max_size=10),
    "question": st.text(min_size=1, max_size=100),
    "expected_answer": st.text(max_size=200),
    "expected_sources": st.lists(st.text(min_size=1, max_size=50), max_size=3),
    "category": st.text(max_size=20),
})

result_strategy = st.fixed_dictionaries({
    "id": st.text(min_size=1, max_size=10),
    "category": st.text(max_size=20),
    "query": st.text(min_size=1, max_size=100),
    "answer": st.text(min_size=1, max_size=200),
    "expected_answer": st.text(max_size=200),
    "faithfulness": st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
    "faithfulness_notes": st.text(max_size=100),
    "relevance": st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
    "relevance_notes": st.text(max_size=100),
    "context_recall": st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
    "context_recall_notes": st.text(max_size=100),
    "completeness": st.one_of(st.none(), st.integers(min_value=1, max_value=5)),
    "completeness_notes": st.text(max_size=100),
    "config_label": st.text(min_size=1, max_size=30),
})


# Feature: rag-eval-scorecard, Property 5: Valid LLM responses are parsed to correct types
# Validates: Requirements 1.2
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(score=st.integers(min_value=1, max_value=5), notes=st.text(min_size=1, max_size=200))
def test_property5_valid_json_parsed_correctly(mock_rag_answer_module, score, notes):
    """Property 5: Valid LLM responses are parsed to correct types."""
    eval_mod = get_eval_module()
    safe_notes = notes.replace('"', "'").replace("\\", "/")
    raw = json.dumps({"score": score, "notes": safe_notes})
    result = eval_mod._parse_judge_response(raw)
    assert isinstance(result["score"], int)
    assert 1 <= result["score"] <= 5
    assert isinstance(result.get("notes", ""), str)


# Feature: rag-eval-scorecard, Property 6: Invalid LLM responses produce a parse-error fallback
# Validates: Requirements 1.2
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(raw=st.text(max_size=200))
def test_property6_invalid_json_produces_fallback(mock_rag_answer_module, raw):
    """Property 6: Invalid LLM responses produce a parse-error fallback containing the raw response."""
    eval_mod = get_eval_module()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "score" in parsed:
            score = parsed["score"]
            if isinstance(score, int) and 1 <= score <= 5:
                return  # Skip valid cases
    except (json.JSONDecodeError, ValueError):
        pass

    result = eval_mod._parse_judge_response(raw)
    assert result["score"] is None
    assert f"Parse error: {raw}" == result["notes"]


# Feature: rag-eval-scorecard, Property 7: Context recall source matching is case-insensitive and extension-agnostic
# Validates: Requirements 1.3
_ASCII_ALPHA = "abcdefghijklmnopqrstuvwxyz"
_ASCII_ALNUM = _ASCII_ALPHA + "0123456789"

@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    stem=st.text(min_size=2, max_size=20, alphabet=_ASCII_ALNUM),
    ext=st.sampled_from(["", ".pdf", ".md"]),
)
def test_property7_source_matching_case_insensitive(mock_rag_answer_module, stem, ext):
    """Property 7: Context recall source matching is case-insensitive and extension-agnostic."""
    assume(stem.strip())
    eval_mod = get_eval_module()

    chunk_source = f"docs/{stem.upper()}{ext}"
    chunks = [{"metadata": {"source": chunk_source}, "text": "content", "score": 0.9}]
    expected = f"path/to/{stem.lower()}{ext}"

    result = eval_mod.score_context_recall(chunks, [expected])
    assert result["found"] == 1, f"Expected to find '{stem}' in '{chunk_source}'"
    assert result["recall"] == 1.0


# Feature: rag-eval-scorecard, Property 8: Context recall formula is correct
# Validates: Requirements 1.3
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    total=st.integers(min_value=1, max_value=10),
    found_count=st.integers(min_value=0, max_value=10),
)
def test_property8_recall_formula_correct(mock_rag_answer_module, total, found_count):
    """Property 8: Context recall formula is correct."""
    assume(found_count <= total)
    eval_mod = get_eval_module()

    expected_sources = [f"source_{i}.pdf" for i in range(total)]
    chunks = []
    for i in range(found_count):
        chunks.append({"metadata": {"source": f"docs/source_{i}"}, "text": "x", "score": 0.9})
    for i in range(found_count, total):
        chunks.append({"metadata": {"source": f"docs/unrelated_{i}"}, "text": "x", "score": 0.5})

    result = eval_mod.score_context_recall(chunks, expected_sources)
    expected_recall = found_count / total
    assert abs(result["recall"] - expected_recall) < 1e-9
    assert result["score"] == round(expected_recall * 5)


# Feature: rag-eval-scorecard, Property 4: LLM judge prompts contain all required inputs
# Validates: Requirements 1.1
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    answer=st.text(min_size=1, max_size=100),
    chunks=st.lists(chunk_strategy, min_size=1, max_size=3),
)
def test_property4_faithfulness_prompt_contains_inputs(mock_rag_answer_module, answer, chunks):
    """Property 4: LLM judge prompts contain all required inputs (faithfulness)."""
    captured_prompts = []

    def capture_llm(prompt):
        captured_prompts.append(prompt)
        return '{"score": 4, "notes": "ok"}'

    mock_rag_answer_module.call_llm.side_effect = capture_llm
    eval_mod = get_eval_module()

    with patch.object(eval_mod, "_call_judge_llm", side_effect=capture_llm):
        eval_mod.score_faithfulness(answer, chunks)

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    assert answer in prompt
    for chunk in chunks:
        assert chunk["text"] in prompt


# Feature: rag-eval-scorecard, Property 1: Config parameters are forwarded faithfully
# Validates: Requirements 2.1
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    retrieval_mode=st.sampled_from(["dense", "hybrid"]),
    top_k_search=st.integers(min_value=1, max_value=20),
    top_k_select=st.integers(min_value=1, max_value=10),
    use_rerank=st.booleans(),
    questions=st.lists(question_strategy, min_size=1, max_size=3),
)
def test_property1_config_forwarded_faithfully(
    mock_rag_answer_module, retrieval_mode, top_k_search, top_k_select, use_rerank, questions
):
    """Property 1: Config parameters are forwarded faithfully."""
    rag_calls = []

    def mock_rag(query, retrieval_mode, top_k_search, top_k_select, use_rerank, verbose):
        rag_calls.append({
            "retrieval_mode": retrieval_mode,
            "top_k_search": top_k_search,
            "top_k_select": top_k_select,
            "use_rerank": use_rerank,
        })
        return {"answer": "ok", "sources": [], "chunks_used": [], "config": {}}

    mock_rag_answer_module.rag_answer.side_effect = mock_rag
    mock_rag_answer_module.call_llm.return_value = '{"score": 3, "notes": "ok"}'

    eval_mod = get_eval_module()
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "label": "test",
    }

    with patch.object(eval_mod, "rag_answer", side_effect=mock_rag):
        eval_mod.run_scorecard(config, test_questions=questions, verbose=False)

    assert len(rag_calls) == len(questions)
    for c in rag_calls:
        assert c["retrieval_mode"] == retrieval_mode
        assert c["top_k_search"] == top_k_search
        assert c["top_k_select"] == top_k_select
        assert c["use_rerank"] == use_rerank


# Feature: rag-eval-scorecard, Property 2: Exception messages are preserved in result rows
# Validates: Requirements 2.2
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(msg=st.text(max_size=100))
def test_property2_exception_message_preserved(mock_rag_answer_module, msg):
    """Property 2: Exception messages are preserved in result rows."""
    mock_rag_answer_module.call_llm.return_value = '{"score": 3, "notes": "ok"}'
    eval_mod = get_eval_module()

    questions = [make_question()]
    config = {"retrieval_mode": "dense", "top_k_search": 5, "top_k_select": 3, "use_rerank": False, "label": "test"}

    with patch.object(eval_mod, "rag_answer", side_effect=Exception(msg)):
        results = eval_mod.run_scorecard(config, test_questions=questions, verbose=False)

    assert len(results) == 1
    assert results[0]["answer"] == f"ERROR: {msg}"


# Feature: rag-eval-scorecard, Property 3: Result rows contain all required fields
# Validates: Requirements 2.3
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(questions=st.lists(question_strategy, min_size=1, max_size=5))
def test_property3_result_rows_have_all_fields(mock_rag_answer_module, questions):
    """Property 3: Result rows contain all required fields."""
    mock_rag_answer_module.call_llm.return_value = '{"score": 4, "notes": "ok"}'
    eval_mod = get_eval_module()

    config = {"retrieval_mode": "dense", "top_k_search": 5, "top_k_select": 3, "use_rerank": False, "label": "test"}
    required_keys = {
        "id", "category", "query", "answer", "expected_answer",
        "faithfulness", "faithfulness_notes",
        "relevance", "relevance_notes",
        "context_recall", "context_recall_notes",
        "completeness", "completeness_notes",
        "config_label",
    }

    with patch.object(eval_mod, "rag_answer", side_effect=NotImplementedError("not impl")):
        results = eval_mod.run_scorecard(config, test_questions=questions, verbose=False)

    for row in results:
        assert required_keys.issubset(set(row.keys())), f"Missing keys: {required_keys - set(row.keys())}"


# Feature: rag-eval-scorecard, Property 9: None scores are excluded from averages in compare_ab
# Validates: Requirements 3.1
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(scores=st.lists(st.one_of(st.none(), st.integers(min_value=1, max_value=5)), min_size=0, max_size=10))
def test_property9_none_excluded_from_averages(mock_rag_answer_module, scores):
    """Property 9: None scores are excluded from averages in compare_ab."""
    eval_mod = get_eval_module()

    non_none = [s for s in scores if s is not None]
    expected_avg = sum(non_none) / len(non_none) if non_none else None

    baseline = [
        {**make_result_row(qid=str(i), config_label="baseline"), "faithfulness": s}
        for i, s in enumerate(scores)
    ]
    variant = []

    import io
    from contextlib import redirect_stdout
    f = io.StringIO()
    with redirect_stdout(f):
        eval_mod.compare_ab(baseline, variant)
    output = f.getvalue()

    if expected_avg is None:
        assert "N/A" in output
    else:
        assert f"{expected_avg:.2f}" in output


# Feature: rag-eval-scorecard, Property 12: Scorecard Markdown contains summary and per-question tables
# Validates: Requirements 4.1
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(results=st.lists(result_strategy, min_size=1, max_size=5))
def test_property12_markdown_contains_both_tables(mock_rag_answer_module, results):
    """Property 12: Scorecard Markdown contains summary and per-question tables."""
    eval_mod = get_eval_module()
    md = eval_mod.generate_scorecard_summary(results, "test_label")

    assert "## Summary" in md
    assert "## Per-Question Results" in md
    assert "| Metric |" in md
    assert "| ID |" in md


# Feature: rag-eval-scorecard, Property 13: AB comparison CSV contains all rows from both configs
# Validates: Requirements 3.2
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    baseline=st.lists(result_strategy, min_size=0, max_size=5),
    variant=st.lists(result_strategy, min_size=0, max_size=5),
)
def test_property13_csv_row_count(mock_rag_answer_module, baseline, variant, tmp_path):
    """Property 13: AB comparison CSV contains all rows from both configs."""
    eval_mod = get_eval_module()

    if not baseline and not variant:
        return

    with patch.object(eval_mod, "RESULTS_DIR", tmp_path):
        eval_mod.compare_ab(baseline, variant, output_csv="test_ab.csv")

    csv_path = tmp_path / "test_ab.csv"
    if not csv_path.exists():
        assert len(baseline) + len(variant) == 0
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == len(baseline) + len(variant)
    for row in rows:
        assert "config_label" in row


# Feature: rag-eval-scorecard, Property 10: Grading log entries contain all required fields
# Validates: Requirements 5.1
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(questions=st.lists(question_strategy, min_size=1, max_size=5))
def test_property10_grading_log_entries_have_all_fields(mock_rag_answer_module, questions, tmp_path):
    """Property 10: Grading log entries contain all required fields."""
    mock_rag_answer_module.call_llm.return_value = '{"score": 4, "notes": "ok"}'
    eval_mod = get_eval_module()

    questions_path = tmp_path / "questions.json"
    questions_path.write_text(json.dumps(questions), encoding="utf-8")
    output_path = tmp_path / "logs" / "grading_run.json"

    config = {"retrieval_mode": "dense", "top_k_search": 5, "top_k_select": 3, "use_rerank": False, "label": "test"}

    with patch.object(eval_mod, "rag_answer", return_value={
        "answer": "ok", "sources": ["src.txt"], "chunks_used": [make_chunk()], "config": {}
    }):
        eval_mod.run_grading_log(questions_path, config, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    required_fields = {"id", "question", "answer", "sources", "chunks_retrieved", "retrieval_mode", "timestamp"}
    assert len(entries) == len(questions)
    for entry in entries:
        assert required_fields.issubset(set(entry.keys()))
        datetime.fromisoformat(entry["timestamp"])


# Feature: rag-eval-scorecard, Property 11: Grading log error entries preserve exception messages
# Validates: Requirements 5.2
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(msg=st.text(max_size=100))
def test_property11_grading_log_error_entries(mock_rag_answer_module, msg, tmp_path):
    """Property 11: Grading log error entries preserve exception messages."""
    eval_mod = get_eval_module()

    questions = [make_question("Q1"), make_question("Q2")]
    questions_path = tmp_path / "questions.json"
    questions_path.write_text(json.dumps(questions), encoding="utf-8")
    output_path = tmp_path / "logs" / "grading_run.json"

    config = {"retrieval_mode": "dense", "top_k_search": 5, "top_k_select": 3, "use_rerank": False, "label": "test"}

    with patch.object(eval_mod, "rag_answer", side_effect=Exception(msg)):
        eval_mod.run_grading_log(questions_path, config, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    assert len(entries) == 2
    for entry in entries:
        assert entry["answer"] == f"PIPELINE_ERROR: {msg}"
        assert entry["sources"] == []
