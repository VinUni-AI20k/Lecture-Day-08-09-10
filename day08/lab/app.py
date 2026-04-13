from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import os

app = FastAPI(title="Lucid RAG Demo")

# Cấu hình static folder
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ChatRequest(BaseModel):
    query: str
    retrieval_mode: str = "hybrid"
    threshold: float = 0.35
    use_hyde: bool = False

@app.get("/")
async def get_index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.post("/api/chat")
async def chat_api(req: ChatRequest):
    # Giả lập delay của LLM và retrieval (1.5 giây)
    await asyncio.sleep(1.5)
    
    # Logic giả lập (Dummy Data)
    # Giả lập trường hợp bị Abstain do Threshold quá cao hoặc query ảo
    if req.threshold > 0.8 or "lỗi abc" in req.query.lower():
        return {
            "answer": "Không tìm thấy thông tin phù hợp trong hệ thống với ngưỡng tin cậy hiện tại. Vui lòng thử lại với các từ khóa khác.",
            "sources": [],
            "chunks_used": [],
            "latency_ms": 1520
        }

    # Giả lập trả lời thành công
    return {
        "answer": f"[DEV MODE - {req.retrieval_mode.upper()} SEARCH] Dựa trên các tài liệu chính sách, câu trả lời cho yêu cầu của bạn là: Thời gian phân loại ticket và xử lý SLA tiêu chuẩn là 24 giờ. Đối với các vấn đề khẩn cấp đánh dấu P1, yêu cầu sẽ được xử lý trong vòng 2 giờ.",
        "sources": ["policy_sla.pdf", "refund_guide.docx"],
        "chunks_used": [
            {
                "id": "CHUNK 1",
                "source": "policy_sla.pdf",
                "section": "Section 1.2",
                "score": 0.89,
                "text": "Thời gian phản hồi cho mức độ Ưu tiên 1 là 2 giờ làm việc. Đối với các yêu cầu không khẩn cấp, SLA chuẩn là 24 giờ..."
            },
            {
                "id": "CHUNK 2",
                "source": "refund_guide.docx",
                "section": "Intro",
                "score": 0.72,
                "text": "Chính sách hoàn tiền áp dụng cho tất cả các gói dịch vụ cao cấp trong vòng 30 ngày kể từ ngày kích hoạt..."
            }
        ],
        "latency_ms": 1520
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
