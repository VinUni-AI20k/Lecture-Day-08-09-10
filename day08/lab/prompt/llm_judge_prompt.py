"""
Prompt templates for LLM-as-Judge evaluation
===================================================================
Tập trung tất cả judge prompts ở đây để dễ chỉnh sửa và A/B test prompt.
"""


def build_answer_relevance_prompt(query: str, answer: str) -> str:
    """
    Answer Relevance judge prompt.
    Đánh giá: câu trả lời có trả lời đúng câu hỏi người dùng không?

    Args:
        query: Câu hỏi gốc của người dùng
        answer: Câu trả lời của RAG pipeline cần chấm

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    return f"""You are a strict answer relevance evaluator for a RAG system.

Your task: determine whether the answer directly and correctly addresses the question asked.
Focus only on whether the answer is on-topic and responsive — not whether it is factually correct.

Scoring rubric (1-5):
  5 = Answer directly and completely addresses the question
  4 = Mostly on-target; missing one minor aspect of the question
  3 = Partially relevant but does not address the core of the question
  2 = Answer is tangentially related but largely off-topic
  1 = Answer does not address the question at all

Question:
{query}

Answer to evaluate:
{answer}

Respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{{"score": <integer 1-5>, "reason": "<one sentence explaining the score>"}}"""


def build_context_recall_prompt(query: str, context_str: str, expected_sources: list) -> str:
    """
    Context Recall judge prompt.
    Đánh giá: retrieved context có chứa đủ thông tin để trả lời câu hỏi không?

    Args:
        query: Câu hỏi gốc của người dùng
        context_str: Toàn bộ retrieved chunks đã được format thành chuỗi
        expected_sources: Danh sách tên file/source cần có trong retrieved chunks

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    sources_str = ", ".join(expected_sources) if expected_sources else "not specified"
    return f"""You are a strict context recall evaluator for a RAG system.

Your task: determine whether the retrieved context contains sufficient information to answer the question.
Expected sources that should be present: {sources_str}

Scoring rubric (1-5):
  5 = Retrieved context fully covers all information needed to answer the question
  4 = Context mostly covers the question; one minor detail is missing
  3 = Context partially covers the question; some key information is absent
  2 = Context is mostly insufficient; major information needed is missing
  1 = Context contains almost nothing relevant to the question

Question:
{query}

Retrieved context:
{context_str}

Respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{{"score": <integer 1-5>, "reason": "<one sentence explaining the score>"}}"""


def build_completeness_prompt(query: str, answer: str, expected_answer: str) -> str:
    """
    Completeness judge prompt.
    Đánh giá: answer có bao phủ đủ các điểm quan trọng trong expected_answer không?

    Args:
        query: Câu hỏi gốc của người dùng
        answer: Câu trả lời của RAG pipeline cần chấm
        expected_answer: Câu trả lời mẫu (ground truth)

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    return f"""You are a strict completeness evaluator for a RAG system.

Your task: compare the model answer against the expected answer and determine how completely
the model answer covers all key points. Do not penalize different wording — only penalize missing information.

Scoring rubric (1-5):
  5 = All key points from the expected answer are present in the model answer
  4 = One minor point is missing
  3 = Some important points are missing
  2 = Many important points are missing
  1 = Most of the core content is missing

Question:
{query}

Expected answer (ground truth):
{expected_answer}

Model answer to evaluate:
{answer}

Respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{{"score": <integer 1-5>, "reason": "<one sentence explaining the score>", "missing_points": ["<point1>", "<point2>"]}}"""


def build_faithfulness_prompt(answer: str, context_str: str) -> str:
    """
    Faithfulness judge prompt.
    Đánh giá: câu trả lời có bám đúng retrieved context không?

    Args:
        answer: Câu trả lời của RAG pipeline cần chấm
        context_str: Toàn bộ retrieved chunks đã được format thành chuỗi

    Returns:
        Prompt string sẵn sàng gửi cho LLM judge
    """
    return f"""You are a strict faithfulness evaluator for a RAG system.

Your task: determine whether the answer is fully grounded in the retrieved context below.
Do NOT use any external knowledge — only judge based on what the context contains.

Scoring rubric (1-5):
  5 = Every claim in the answer is directly supported by the retrieved context
  4 = Almost fully grounded; one minor detail is uncertain
  3 = Mostly grounded, but some information may come from model knowledge
  2 = Several claims are not found in the retrieved context
  1 = Answer is largely hallucinated or contradicts the context

Retrieved context:
{context_str}

Answer to evaluate:
{answer}

Respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{{"score": <integer 1-5>, "reason": "<one sentence explaining the score>"}}"""
