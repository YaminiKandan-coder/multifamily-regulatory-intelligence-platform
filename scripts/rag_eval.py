"""RAG evaluation harness. Loads data/eval/eval_dataset.json and evaluates retrieval + answer."""
from __future__ import annotations
import argparse
import json
from typing import Any
from core.rag.qa_system import get_qa
from db.client import get_db


def evaluate(retrieval_only: bool = False) -> list[dict[str, Any]]:
    with open("data/eval/eval_dataset.json", encoding="utf-8") as f:
        dataset = json.load(f)

    qa = get_qa()
    results = []

    for case in dataset:
        case_id = case.get("id", "unknown")
        query = case.get("query", "")
        expected_keywords = case.get("expected_keywords", [])
        jurisdiction_id = case.get("jurisdiction_id")

        print(f"Evaluating: {case_id}")

        if retrieval_only:
            # Just check that we get chunks back
            from core.llm.client import llm
            from core.rag.hybrid import hybrid_search
            try:
                emb = llm.embed(query)
                chunks = hybrid_search(
                    query=query,
                    query_embedding=emb,
                    db_client=get_db(),
                    top_n=5,
                    jurisdiction_id=jurisdiction_id,
                )
                retrieved = [c.get("chunk_text", "") for c in chunks]
            except Exception as e:
                retrieved = []
                print(f"  Error: {e}")
            result = {
                "id": case_id,
                "retrieved_count": len(retrieved),
                "keyword_hits": sum(
                    1 for kw in expected_keywords
                    if any(kw.lower() in r.lower() for r in retrieved)
                ),
            }
        else:
            try:
                grounded = qa.answer(query=query, jurisdiction_id=jurisdiction_id)
                answer = grounded.answer
                confidence = grounded.confidence
            except Exception as e:
                answer = ""
                confidence = "error"
                print(f"  Error: {e}")

            keyword_hits = sum(1 for kw in expected_keywords if kw.lower() in answer.lower())
            result = {
                "id": case_id,
                "confidence": confidence,
                "keyword_hits": keyword_hits,
                "total_keywords": len(expected_keywords),
                "answer_length": len(answer),
                "answer_preview": answer[:200],
            }

        results.append(result)
        print(f"  Result: {result}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()

    results = evaluate(retrieval_only=args.retrieval_only)

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nEvaluation complete. {len(results)} cases. Results saved to eval_results.json.")


if __name__ == "__main__":
    main()
