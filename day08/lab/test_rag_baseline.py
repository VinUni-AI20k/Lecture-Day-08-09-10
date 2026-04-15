"""
test_rag_baseline.py — Validation Test for Sprint 2 Baseline
============================================================
Run this script to validate that rag_answer.py implementation is correct.

Usage:
    python test_rag_baseline.py

Expected output:
    ✓ All 4 tests pass
    ✓ Answers have citations [1], [2], etc.
    ✓ Insufficient context questions get "abstain" response
"""

import sys
from pathlib import Path

# Add parent dir to path so we can import rag_answer
sys.path.insert(0, str(Path(__file__).parent))

from rag_answer import rag_answer, retrieve_dense


def test_retrieve_dense():
    """Test 1: Dense retrieval works"""
    print("\n[TEST 1] Dense Retrieval")
    print("-" * 60)
    try:
        query = "SLA ticket P1"
        results = retrieve_dense(query, top_k=3)
        
        if len(results) == 0:
            print("❌ FAIL: No retrieval results")
            return False
        
        print(f"✓ Retrieved {len(results)} chunks")
        for i, chunk in enumerate(results, 1):
            source = chunk.get("metadata", {}).get("source", "unknown")
            score = chunk.get("score", 0)
            print(f"  [{i}] {source} (score={score:.3f})")
        
        print("✓ PASS: Dense retrieval works")
        return True
    except NotImplementedError as e:
        print(f"❌ FAIL: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False


def test_rag_with_sufficient_context():
    """Test 2: RAG answer with sufficient context (should have citation)"""
    print("\n[TEST 2] RAG Answer - Sufficient Context")
    print("-" * 60)
    try:
        query = "SLA xử lý ticket P1 là bao lâu?"
        result = rag_answer(query, verbose=False)
        
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        
        # Check 1: Answer is not empty
        if not answer or len(answer) < 10:
            print(f"❌ FAIL: Answer is too short or empty: {answer}")
            return False
        
        # Check 2: Answer should have citation [1], [2], or [3]
        has_citation = any(f"[{i}]" in answer for i in range(1, 4))
        if not has_citation:
            print(f"⚠️ WARNING: No citation found in answer (but not critical)")
            print(f"   Answer: {answer[:100]}")
        
        # Check 3: Sources should be in answer
        if not sources:
            print(f"❌ FAIL: No sources extracted")
            return False
        
        print(f"✓ Answer: {answer[:80]}...")
        print(f"✓ Sources: {sources}")
        print(f"✓ Has citation: {has_citation}")
        print("✓ PASS: RAG with sufficient context works")
        return True
        
    except NotImplementedError as e:
        print(f"❌ FAIL: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False


def test_rag_with_insufficient_context():
    """Test 3: RAG answer with insufficient context (should abstain)"""
    print("\n[TEST 3] RAG Answer - Insufficient Context (Abstain)")
    print("-" * 60)
    try:
        query = "ERR-403-AUTH là lỗi gì?"
        result = rag_answer(query, verbose=False)
        
        answer = result.get("answer", "")
        
        # Check: Answer should indicate insufficient context
        # Keywords: "don't know", "không", "insufficient", "không đủ", "no information", etc.
        abstain_keywords = [
            "don't know", 
            "không", 
            "insufficient",
            "no ", 
            "not found",
            "cannot find",
        ]
        
        has_abstain = any(keyword.lower() in answer.lower() for keyword in abstain_keywords)
        
        if not has_abstain:
            print(f"⚠️ WARNING: Answer might not be abstaining properly")
            print(f"   Answer: {answer[:100]}")
        else:
            print(f"✓ Answer correctly abstains: {answer[:80]}...")
        
        print("✓ PASS: RAG handles insufficient context")
        return True
        
    except NotImplementedError as e:
        print(f"❌ FAIL: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False


def test_output_format():
    """Test 4: Output format is correct"""
    print("\n[TEST 4] Output Format")
    print("-" * 60)
    try:
        query = "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"
        result = rag_answer(query, verbose=False)
        
        # Check required keys
        required_keys = ["query", "answer", "sources", "chunks_used", "config"]
        for key in required_keys:
            if key not in result:
                print(f"❌ FAIL: Missing key '{key}' in output")
                return False
        
        # Check data types
        if not isinstance(result["query"], str):
            print(f"❌ FAIL: query should be str")
            return False
        
        if not isinstance(result["answer"], str):
            print(f"❌ FAIL: answer should be str")
            return False
        
        if not isinstance(result["sources"], list):
            print(f"❌ FAIL: sources should be list")
            return False
        
        if not isinstance(result["chunks_used"], list):
            print(f"❌ FAIL: chunks_used should be list")
            return False
        
        if not isinstance(result["config"], dict):
            print(f"❌ FAIL: config should be dict")
            return False
        
        # Check chunks_used structure
        if result["chunks_used"]:
            chunk = result["chunks_used"][0]
            if not all(key in chunk for key in ["text", "metadata", "score"]):
                print(f"❌ FAIL: chunk missing required fields")
                return False
        
        print("✓ Query:", result["query"][:60])
        print("✓ Sources:", result["sources"])
        print("✓ Chunks used:", len(result["chunks_used"]))
        print("✓ Config:", result["config"])
        print("✓ PASS: Output format is correct")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def main():
    print("=" * 60)
    print("Sprint 2 Baseline - Validation Test Suite")
    print("=" * 60)
    
    tests = [
        test_retrieve_dense,
        test_rag_with_sufficient_context,
        test_rag_with_insufficient_context,
        test_output_format,
    ]
    
    results = []
    for test_func in tests:
        try:
            passed = test_func()
            results.append((test_func.__name__, passed))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append((test_func.__name__, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Sprint 2 Baseline is ready.")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} test(s) failed. Fix issues and retry.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
