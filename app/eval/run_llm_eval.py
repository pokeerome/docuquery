import sys
import os
import json
from datetime import datetime, timezone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.query import answer_question
from app.eval.golden_set import GOLDEN_SET
from app.eval.judge import judge_faithfulness, judge_relevancy

TEST_USER_ID = 1
EVAL_LOG_FILE = "data/llm_eval_log.jsonl"


def run_llm_evaluation():
    results = []

    for item in GOLDEN_SET:
        question = item["question"]

        answer, chunk_texts = answer_question(question, user_id=TEST_USER_ID, return_context=True)
        context = "\n\n".join(chunk_texts)

        faithfulness_result = judge_faithfulness(question, answer, context)
        relevancy_result = judge_relevancy(question, answer)

        result = {
            "question": question,
            "answer": answer,
            "should_be_answerable": item["should_be_answerable"],
            "faithfulness_score": faithfulness_result["score"],
            "faithfulness_reason": faithfulness_result["reason"],
            "relevancy_score": relevancy_result["score"],
            "relevancy_reason": relevancy_result["reason"],
        }
        results.append(result)

        print(f"Q: {question}")
        print(f"A: {answer}")
        print(f"  Faithfulness: {faithfulness_result['score']} — {faithfulness_result['reason']}")
        print(f"  Relevancy:    {relevancy_result['score']} — {relevancy_result['reason']}")
        print()

    valid_faithfulness = [r["faithfulness_score"] for r in results if r["faithfulness_score"] is not None]
    avg_faithfulness = sum(valid_faithfulness) / len(valid_faithfulness) if valid_faithfulness else None

    answerable_relevancy = [
        r["relevancy_score"] for r in results
        if r["should_be_answerable"] and r["relevancy_score"] is not None
    ]

    avg_answerable_relevancy = sum(answerable_relevancy) / len(answerable_relevancy) if answerable_relevancy else None

    unanswerable_correct = [
        1 for r in results
        if not r["should_be_answerable"] and any(
            phrase in r["answer"].lower() for phrase in ["don't know", "cannot", "no information"]
        )
    ]
    unanswerable_total = sum(1 for r in results if not r["should_be_answerable"])
    refusal_accuracy = len(unanswerable_correct) / unanswerable_total if unanswerable_total else None

    print("=" * 50)
    print(f"Average Faithfulness (all questions):        {avg_faithfulness:.2f}" if avg_faithfulness is not None else "Average Faithfulness: N/A")
    print(f"Average Relevancy (answerable questions):     {avg_answerable_relevancy:.2f}" if avg_answerable_relevancy is not None else "Average Relevancy (answerable): N/A")
    print(f"Correct refusal rate (unanswerable questions): {refusal_accuracy:.0%}" if refusal_accuracy is not None else "Refusal accuracy: N/A")

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "avg_faithfulness": avg_faithfulness,
        "avg_answerable_relevancy": avg_answerable_relevancy,
        "refusal_accuracy": refusal_accuracy,
        "results": results,
    }
    with open(EVAL_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return results


if __name__ == "__main__":
    run_llm_evaluation()