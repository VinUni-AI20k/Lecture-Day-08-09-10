# Individual Report — Lab Day 08: RAG Pipeline

**Name:** Nguyen Minh Hieu (Student ID: 2A202600180)  
**Role:** Documentation Owner  
**Submission Date:** 13/04/2026  
**Required Length:** 500–800 words

---

## 1. What did I do in this lab? (100-150 words)

> In this lab, my primary responsibility was acting as the Documentation Owner, focusing mainly on Sprint 2 and Sprint 3.
Specifically, I was in charge of drafting and updating the `architecture.md` file to clearly outline the architectural flow of the entire RAG system. Furthermore, I spent a significant amount of time analyzing the automated evaluation results from the Baseline and Variant models. Relying on `ab_comparison.csv` and other scorecard files, I diagnosed errors, compared performance metrics, documented the tuning process, and completed the `tuning-log.md`. Thanks to my clear reporting and visual documentation, our team could easily make the final decision to select the Hybrid Search + Rerank architecture and had concrete data to back up this choice.

---

## 2. What concept did I understand better after this lab? (100-150 words)

> One concept that became extremely clear to me during this lab is the combination of **Hybrid Retrieval** and **Cross-encoder Reranking**. 
Previously, I thought Dense Embedding models (Vector Similarity) were magic bullets that could solve all search problems. However, when the system encountered questions with tricky or precise anchor keywords, the Dense model sometimes struggled. By integrating Sparse Search (BM25) — utilizing precise keyword tokenization — we instantly filled this gap, allowing the system to extract chunks containing exact keywords. Although fusing two sources via RRF (Reciprocal Rank Fusion) introduces some noise, the secondary verification provided by the Cross-Encoder (Rerank) scoring guarantees that the three most accurate and logically sound chunks are pushed into the Grounded Prompt.

---

## 3. What surprised or challenged me? (100-150 words)

> The most surprising aspect, which was also the biggest hurdle during data analysis, was the "out of phase" phenomenon among evaluator metrics.
Normally, one expects all metrics to universally increase when the pipeline improves. However, in Variant 1, while `Answer Relevance` improved on average due to better target context selection, the `Faithfulness` score slightly dropped (from 4.20 down to 4.10). The reason is that when too much mixed information from the Hybrid retrieval is injected at once, the generation model (gpt-4o-mini) sometimes behaves loosely, randomly synthesizing or hallucinating details about exceptions (e.g., the digital license product policy). This made me realize that there is no perfect configuration; RAG tuning requires delicate trade-offs and constant metric monitoring.

---

## 4. Scorecard Question Analysis (150-200 words)

**Question:** *q10: "Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?" (If an urgent refund is needed for a VIP customer, is the process different?)*

**Analysis:** 
- This query is quite deceptive because the term "VIP customer" is not explicitly categorized in the underlying standard operating documents. 
- In the **Baseline (Dense Search)**, this query received a Relevance of 1/5 and a Completeness of 2/5. While the dense model retrieved the correct Refund Policy file, the LLM rigidly responded with an "I don't know" assertion simply because the "VIP" keyword was absent.
- In **Variant (Hybrid + Rerank)**, the relevance improved to 3/5 and completeness to 3/5. The hybrid search effectively pulled the comprehensive refund policy text for the cross-encoder to lock down. With a much solid context foundation, the generation module confidently inferred based on the text: "The document does not detail any specific process for VIPs, so VIP customers still follow the standard 3-5 day refund process." Helping the LLM confidently infer general procedures for specific cases successfully shattered the model's rigid refusal to answer.

---

## 5. What would I do with extra time? (50-100 words)

> If given an extra hour for Sprint 4, I would like to experiment with **Query Transformation** techniques (such as HyDE - Hypothetical Document Embeddings) before the search phase. HyDE asks the LLM to generate a hypothetical answer based on its professional knowledge, and then uses that generated text to search the database. This effectively solves the blind spots of keyword search when dealing with short or vague queries, guiding the retrieval mechanism to match meaning even when users provide poor keywords.
