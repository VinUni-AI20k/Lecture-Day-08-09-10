"""Test rerank on gq06 to see if ext. 9999 gets promoted."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rag_answer import retrieve_dense, rerank as do_rerank

q = "Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?"

print("=== Dense top-20 → Rerank top-10 ===")
pool = retrieve_dense(q, top_k=20)
reranked = do_rerank(q, pool, top_k=10)
for i, c in enumerate(reranked):
    meta = c.get("metadata", {})
    has_9999 = "9999" in c.get("text", "")
    marker = " *** EXT.9999 ***" if has_9999 else ""
    print(f"  [{i+1:2d}] rerank={c.get('rerank_score',0):.4f} | {meta.get('source',''):30s} | {meta.get('section',''):40s}{marker}")

print("\n=== Dense top-28 → Rerank top-12 ===")
pool2 = retrieve_dense(q, top_k=28)
reranked2 = do_rerank(q, pool2, top_k=12)
for i, c in enumerate(reranked2):
    meta = c.get("metadata", {})
    has_9999 = "9999" in c.get("text", "")
    marker = " *** EXT.9999 ***" if has_9999 else ""
    print(f"  [{i+1:2d}] rerank={c.get('rerank_score',0):.4f} | {meta.get('source',''):30s} | {meta.get('section',''):40s}{marker}")
