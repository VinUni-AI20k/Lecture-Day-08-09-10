"""Debug 3 câu Partial: xem chunks retrieved và answer hiện tại."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rag_answer import retrieve_dense, build_context_block, build_grounded_prompt, call_llm

QUERIES = {
    "gq02": "Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?",
    "gq04": "Nếu chọn nhận store credit thay vì hoàn tiền, tôi được bao nhiêu phần trăm so với số tiền gốc?",
    "gq06": "Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?",
}

for qid, query in QUERIES.items():
    print(f"\n{'='*70}")
    print(f"[{qid}] {query}")
    print('='*70)
    
    candidates = retrieve_dense(query, top_k=20)
    for i, c in enumerate(candidates[:12]):
        meta = c.get("metadata", {})
        src = meta.get("source", "?")
        sec = meta.get("section", "")
        score = c.get("score", 0)
        preview = c.get("text", "")[:120].replace("\n", " ")
        print(f"  [{i+1:2d}] score={score:.4f} | {src:30s} | {sec:30s} | {preview}")
    
    selected = candidates[:8]
    ctx = build_context_block(selected)
    prompt = build_grounded_prompt(query, ctx)
    answer = call_llm(prompt)
    print(f"\n  ANSWER: {answer[:500]}")
    print(f"  Sources in top-8: {set(c['metadata'].get('source','?') for c in selected)}")
