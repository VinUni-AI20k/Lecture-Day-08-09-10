"""Find ext. 9999 chunk rank for gq06."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rag_answer import retrieve_dense

q = "Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?"
candidates = retrieve_dense(q, top_k=29)

for i, c in enumerate(candidates):
    text = c.get("text", "")
    if "9999" in text or "kênh liên lạc" in text.lower() or "công cụ" in text.lower():
        meta = c.get("metadata", {})
        print(f"  RANK {i+1}: score={c['score']:.4f} | {meta.get('source','')} | {meta.get('section','')}")
        print(f"    TEXT: {text[:200]}")
        print()

print("\n--- Also check rank of all sla-p1 chunks ---")
for i, c in enumerate(candidates):
    meta = c.get("metadata", {})
    if "sla" in meta.get("source", "").lower():
        print(f"  RANK {i+1}: score={c['score']:.4f} | {meta.get('section','')} | {c['text'][:100]}")
