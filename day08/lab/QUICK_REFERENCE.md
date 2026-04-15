# 🚀 SPRINT 2 QUICK REFERENCE CARD

## In Your Hand (Sprint 2 Completed)

### 3 Main Functions Implemented

```
1️⃣  retrieve_dense()
    └─ Input: query string
    └─ Output: List[{text, metadata, score}]
    └─ Does: Query ChromaDB by embedding similarity

2️⃣  call_llm()
    └─ Input: prompt string
    └─ Output: LLM response string
    └─ Does: OpenAI OR Gemini (auto-detect API key)

3️⃣  rag_answer()
    └─ Input: query + config
    └─ Output: {answer, sources, chunks_used, config}
    └─ Does: Complete RAG pipeline (retrieve→generate)
```

---

## One-Minute Quickstart

```bash
# 1. Setup (first time only)
pip install -r requirements.txt
# Edit .env:  OPENAI_API_KEY=sk-... OR GOOGLE_API_KEY=...

# 2. Run baseline
python rag_answer.py

# 3. Run tests
python test_rag_baseline.py

# 4. Test one query
python -c "from rag_answer import rag_answer; print(rag_answer('SLA P1?')['answer'])"
```

---

## Citation Format (KEY!)

Your answers MUST have [1], [2], [3] for eval.py to work:

```
❌ WRONG: "SLA đối với ticket P1 là 15 phút"
✅ RIGHT: "SLA đối với ticket P1 là 15 phút [1]"

❌ WRONG: "P1 tickets get escalated"
✅ RIGHT: "P1 tickets get escalated after 10 minutes [2]"
```

---

## API Configuration (Pick ONE)

### OpenAI (Recommended - Cheaper)

```bash
OPENAI_API_KEY=sk-YOUR_KEY_HERE
```

### Google Gemini (Free tier)

```bash
GOOGLE_API_KEY=YOUR_GEMINI_KEY
```

---

## What Each Score Means

```
score = 1 - distance  (ChromaDB cosine)

score ≥ 0.8  → Very relevant, include in prompt
score 0.6-0.8 → Somewhat relevant, maybe include
score < 0.6  → Weak match, exclude
```

---

## Abstain Examples

Your prompt FORCES these behaviors:

✅ Sufficient context:

```
Q: "SLA xử lý ticket P1 là bao lâu?"
A: "Ticket P1 có SLA phản hồi 15 phút, xử lý 4 giờ. [1]"
```

✅ Insufficient context (ABSTAIN):

```
Q: "ERR-403-AUTH là lỗi gì?"
A: "Tôi không tìm thấy thông tin về lỗi ERR-403-AUTH trong tài liệu hiện có."
```

---

## Output Structure (For Evaluation)

```python
result = {
    "query": "Your question",
    "answer": "Answer with [1] citations",         ← LLM output
    "sources": ["sla_p1_2026.txt"],               ← For citation checking
    "chunks_used": [{...}, {...}, {...}],         ← For faithfulness eval
    "config": {                                    ← For reproducibility
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False
    }
}
```

---

## Troubleshooting Matrix

| Problem         | Solution      | Command                         |
| --------------- | ------------- | ------------------------------- |
| No chunks found | Run index.py  | `python ../index.py`            |
| API key error   | Edit .env     | Edit `.env` file                |
| Empty answer    | Check API key | Verify in `.env`                |
| Wrong citations | Prompt issue  | Check `build_grounded_prompt()` |

---

## Test Commands

```bash
# All tests (RECOMMENDED)
python test_rag_baseline.py

# Quick retrieval test
python -c "from rag_answer import retrieve_dense; print(len(retrieve_dense('SLA', 3)))"

# Full pipeline test
python rag_answer.py

# Single query
python -c "from rag_answer import rag_answer; print(rag_answer('SLA P1?')['answer'])"
```

---

## Temperature Explanation

```
temperature=0   → Same answer every time (for testing) ✅ BASELINE
temperature=0.5 → Some variety
temperature=1.0 → Lots of variation (for creative tasks)

Baseline MUST use temperature=0 ✅
```

---

## Files You Own

| File                   | What      | Action                               |
| ---------------------- | --------- | ------------------------------------ |
| rag_answer.py          | Main code | ✅ Complete, test it                 |
| test_rag_baseline.py   | Tests     | ✅ Run `python test_rag_baseline.py` |
| SPRINT_2_QUICKSTART.md | Guide     | Read if confused                     |
| .env                   | Config    | Fill in your API key                 |

---

## Before Passing to Sprint 3 (Việt)

- [x] Run `test_rag_baseline.py` → All 4 tests pass
- [x] Run `python rag_answer.py` → No crashes
- [x] Test on 3+ sample queries → Has citations [1]
- [x] Test abstain → Out-of-scope queries handled

---

## Dense Retrieval Formula

```
1. Embed query with same model as index.py
2. ChromaDB returns top-K nearest neighbors
3. Distance ranges from 0 to 2 (cosine)
4. Convert: score = 1 - distance
5. Filter: Only use chunks with score ≥ threshold
6. Select top-3 for prompt
```

---

## Next Phase (Sprint 3 Tuning)

After you're done, Việt will:

- Pick ONE variant (hybrid/rerank/query-expand)
- Compare baseline vs variant
- Measure improvements
- Document in tuning-log.md

Your baseline is the benchmark → Keep it working!

---

## Key Metrics Sprint 4 Will Check

```
✓ Faithfulness: Does answer match provided context? [1]
✓ Relevance: Does answer match expected answer?
✓ Citation Quality: Are [1], [2], [3] correct?
✓ Abstain Quality: Do answers abstain when appropriate?
```

---

## Emergency Commands

```bash
# If stuck, rerun full setup
pip install -r requirements.txt
python index.py
python test_rag_baseline.py

# If crashed, check last 20 lines
python rag_answer.py 2>&1 | tail -20

# If still stuck, manual test
python -c "
from rag_answer import *
result = rag_answer('SLA P1?', verbose=True)
"
```

---

**🎯 BOTTOM LINE:**

Your implementation is **COMPLETE** and **READY**.

3 functions implemented ✅  
Tests passing ✅  
Documentation done ✅  
Next: Give to Việt for Sprint 3 ✅

---

_Print this card. Keep it on your desk. Good luck! 🚀_
