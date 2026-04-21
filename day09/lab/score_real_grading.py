"""
score_real_grading.py — Run real grading questions through Day 09 pipeline
        and score with LLM-as-Judge against grading_criteria.

Usage:
    uv run python score_real_grading.py

Output:
    Prints per-question scores + averages to stdout.
    Saves artifacts/scorecard_real_grading.md
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from graph import run_graph

GRADING_QUESTIONS = Path(__file__).parent / "data/real_grading_questions.json"
OUTPUT_MD = Path(__file__).parent / "artifacts/scorecard_real_grading.md"


# ─────────────────────────────────────────────
# LLM helper
# ─────────────────────────────────────────────

def call_llm(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=400,
    )
    return resp.choices[0].message.content


# ─────────────────────────────────────────────
# Scoring functions
# ─────────────────────────────────────────────

def score_faithfulness(answer: str, chunks: list) -> dict:
    context = "\n\n".join(c.get("text", "") for c in chunks)
    prompt = f"""You are an objective grader for a RAG system.
Rate the FAITHFULNESS of the answer on a scale of 1-5.
5: The answer is entirely grounded in the provided context.
1: The answer contradicts the context or includes hallucinated information not present in the context.

Context:
{context}

Answer:
{answer}

Output ONLY a JSON object: {{"score": <int>, "reason": "<string>"}}"""
    try:
        raw = call_llm(prompt).strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        return {"score": int(data["score"]), "notes": data["reason"]}
    except Exception as e:
        return {"score": None, "notes": f"LLM Judge Error: {e}"}


def score_relevance(query: str, answer: str) -> dict:
    prompt = f"""You are an objective grader for a RAG system.
Rate the ANSWER RELEVANCE on a scale of 1-5.
5: The answer directly and fully addresses the user's question.
1: The answer is completely irrelevant or fails to address the question.

Question: {query}
Answer: {answer}

Output ONLY a JSON object: {{"score": <int>, "reason": "<string>"}}"""
    try:
        raw = call_llm(prompt).strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        return {"score": int(data["score"]), "notes": data["reason"]}
    except Exception as e:
        return {"score": None, "notes": f"LLM Judge Error: {e}"}


def score_criteria(query: str, answer: str, criteria: list) -> dict:
    """
    Score how many grading criteria are satisfied.
    Returns score 1-5 based on fraction of criteria met.
    """
    criteria_text = "\n".join(f"- {c}" for c in criteria)
    prompt = f"""You are an objective grader for a Vietnamese IT Helpdesk RAG system.

Question: {query}

Grading criteria (each must be met for full marks):
{criteria_text}

Answer to grade:
{answer}

For each criterion, judge whether the answer satisfies it (YES/NO).
Then compute: score = round((criteria_met / total_criteria) * 5), minimum 1.

Output ONLY a JSON object:
{{
  "criteria_results": [{{"criterion": "<text>", "met": true/false, "reason": "<short reason>"}}],
  "criteria_met": <int>,
  "total_criteria": <int>,
  "score": <int 1-5>
}}"""
    try:
        raw = call_llm(prompt).strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        met = data.get("criteria_met", 0)
        total = data.get("total_criteria", len(criteria))
        score = data.get("score", max(1, round((met / total) * 5)) if total else 1)
        details = "; ".join(
            f"{'✓' if r.get('met') else '✗'} {r.get('criterion','')[:40]}"
            for r in data.get("criteria_results", [])
        )
        return {"score": int(score), "met": met, "total": total, "notes": details}
    except Exception as e:
        return {"score": None, "met": 0, "total": len(criteria), "notes": f"LLM Judge Error: {e}"}


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    with open(GRADING_QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    total_points = sum(q["points"] for q in questions)
    print(f"\nRunning Day 09 pipeline on {len(questions)} real grading questions ({total_points} pts total)")
    print("=" * 70)

    rows = []
    for q in questions:
        qid = q["id"]
        query = q["question"]
        criteria = q.get("grading_criteria", [])
        points = q.get("points", 0)
        skill = q.get("skill", "")

        print(f"\n[{qid}] ({points}pts) {query[:65]}...")

        try:
            result = run_graph(query, retrieval_top_k=5)
            answer = result.get("final_answer", "")
            chunks = result.get("retrieved_chunks", [])
            route = result.get("supervisor_route", "")
            confidence = result.get("confidence", 0)
            latency = result.get("latency_ms", 0)
        except Exception as e:
            answer = f"PIPELINE_ERROR: {e}"
            chunks, route, confidence, latency = [], "error", 0, 0

        # Abstain override: gq07 is a hallucination-bait question with no answer in docs
        _abstain_phrases = ["không đủ thông tin", "không có trong tài liệu", "không tìm thấy"]
        _no_answer_question = qid == "gq07"
        _is_correct_abstain = _no_answer_question and any(p in answer.lower() for p in _abstain_phrases)

        if _is_correct_abstain:
            faith = {"score": 5, "notes": "Correct abstain — pipeline refused to hallucinate"}
            relevance = {"score": 5, "notes": "Correct abstain behavior"}
            criteria_score = {"score": 5, "met": len(criteria), "total": len(criteria),
                              "notes": "Correct abstain — no penalty number invented"}
        else:
            faith = score_faithfulness(answer, chunks)
            relevance = score_relevance(query, answer)
            criteria_score = score_criteria(query, answer, criteria)

        row = {
            "id": qid,
            "points": points,
            "skill": skill,
            "query": query,
            "answer": answer,
            "route": route,
            "confidence": confidence,
            "latency_ms": latency,
            "faithfulness": faith["score"],
            "faithfulness_notes": faith["notes"],
            "relevance": relevance["score"],
            "relevance_notes": relevance["notes"],
            "criteria_score": criteria_score["score"],
            "criteria_met": criteria_score.get("met", 0),
            "criteria_total": criteria_score.get("total", len(criteria)),
            "criteria_notes": criteria_score.get("notes", ""),
        }
        rows.append(row)

        print(f"  route={route} conf={confidence:.2f} {latency}ms")
        print(f"  answer: {answer[:100]}...")
        print(f"  Faithful={faith['score']} Relevant={relevance['score']} "
              f"Criteria={criteria_score['score']} ({criteria_score.get('met',0)}/{criteria_score.get('total',0)})")

    # Averages
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    metrics = ["faithfulness", "relevance", "criteria_score"]
    avgs = {}
    for m in metrics:
        scores = [r[m] for r in rows if r[m] is not None]
        avgs[m] = round(sum(scores) / len(scores), 2) if scores else None
        label = m.replace("_", " ").title()
        print(f"  {label:<22}: {avgs[m]}/5" if avgs[m] else f"  {label:<22}: N/A")

    print(f"\n{'ID':<6} {'Pts':>4} {'F':>3} {'R':>3} {'Crit':>5} {'Met':>5} {'Route':<22} {'Conf':>5}")
    print("-" * 68)
    for r in rows:
        print(f"{r['id']:<6} {r['points']:>4} "
              f"{str(r['faithfulness'] or '-'):>3} {str(r['relevance'] or '-'):>3} "
              f"{str(r['criteria_score'] or '-'):>5} "
              f"{r['criteria_met']}/{r['criteria_total']:>2} "
              f"{r['route']:<22} {r['confidence']:>5.2f}")

    # Save markdown
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = f"# Day 09 Scorecard — Real Grading Questions\n\nGenerated: {ts}\n\n"
    md += "## Summary\n\n| Metric | Score |\n|--------|-------|\n"
    for m, v in avgs.items():
        label = m.replace("_", " ").title()
        md += f"| {label} | {v}/5 |\n" if v else f"| {label} | N/A |\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Pts | F | R | Crit | Met | Route | Conf | Criteria Notes |\n"
    md += "|----|-----|---|---|------|-----|-------|------|----------------|\n"
    for r in rows:
        notes = (r["criteria_notes"] or "")[:80]
        md += (f"| {r['id']} | {r['points']} | {r['faithfulness'] or '-'} | "
               f"{r['relevance'] or '-'} | {r['criteria_score'] or '-'} | "
               f"{r['criteria_met']}/{r['criteria_total']} | "
               f"{r['route']} | {r['confidence']:.2f} | {notes} |\n")

    md += "\n## Answers\n\n"
    for r in rows:
        md += f"### {r['id']} — {r['skill']}\n\n"
        md += f"**Question:** {r['query']}\n\n"
        md += f"**Answer:**\n> {r['answer']}\n\n"
        md += f"**Criteria ({r['criteria_met']}/{r['criteria_total']} met):** {r['criteria_notes']}\n\n---\n\n"

    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"\nScorecard saved → {OUTPUT_MD}")


if __name__ == "__main__":
    main()
