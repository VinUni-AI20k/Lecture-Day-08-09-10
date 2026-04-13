import os
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Import the actual retrieval/generation logic
from rag_answer import rag_answer, transform_query

app = FastAPI(title="Lucid RAG Demo")

# Cấu hình static folder
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ChatRequest(BaseModel):
    query: str
    retrieval_mode: str = "hybrid"
    threshold: float = 0.35  # UI still sends this, we can ignore or use it
    use_hyde: bool = False

@app.get("/")
async def get_index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.post("/api/chat")
async def chat_api(req: ChatRequest):
    start_time = time.time()
    
    try:
        # 1. Transform query bằng HyDE nếu User tick chọn
        processed_query = req.query
        if req.use_hyde:
            transformed = transform_query(req.query, strategy="hyde")
            processed_query = transformed[0] if transformed else req.query
            
        # 2. Gọi hàm thực thi RAG Pipeline (từ rag_answer.py thực tế)
        # Sử dụng tham số mode lấy từ thanh Sidebar bên UI (req.retrieval_mode)
        res = rag_answer(
            query=processed_query, 
            retrieval_mode=req.retrieval_mode,
            verbose=False
        )
        
        # 3. Format lại "chunks_used" cho khớp với Trace Panel của UI Demo
        formatted_chunks = []
        for idx, chunk in enumerate(res.get("chunks_used", [])):
            meta = chunk.get("metadata", {})
            formatted_chunks.append({
                "id": f"CHUNK {idx + 1}",
                "source": meta.get("source", "unknown"),
                "section": meta.get("section", "N/A"),
                "score": round(chunk.get("score", 0), 4),
                # Cắt bớt content nếu quá dài để hiển thị mượt trên UI
                "text": chunk.get("text", "")[:400] + ("..." if len(chunk.get("text", "")) > 400 else "")
            })
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "answer": res["answer"],
            "sources": res["sources"],
            "chunks_used": formatted_chunks,
            "latency_ms": latency_ms
        }
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "answer": f"Đã có lỗi hệ thống xảy ra trong quá trình chạy Pipeline: {str(e)}.\n\nVui lòng kiểm tra lại thiết lập biến môi trường (Ví dụ OPENAI_API_KEY).",
            "sources": [],
            "chunks_used": [],
            "latency_ms": latency_ms
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
