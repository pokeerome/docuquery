import sys
import os
import json
from datetime import datetime, timezone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.query import answer_question
from app.eval.golden_set import GOLDEN_SET

TEST_USER_ID = 1
EVAL_LOG_FILE = "data/eval_log.jsonl"


def check_answer(answer: str, expected_keywords: list[str]) -> bool:
    answer_lower = answer.lower()
    return any(keyword.lower() in answer_lower for keyword in expected_keywords)


def run_evaluation():
    results = []

    for item in GOLDEN_SET:
        question = item["question"]
        expected = item["expected_answer_contains"]

        answer = answer_question(question, user_id=TEST_USER_ID)
        passed = check_answer(answer, expected)

        results.append({
            "question": question,
            "answer": answer,
            "expected": expected,
            "passed": passed
        })

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] Q: {question}")
        print(f"       A: {answer}")
        print()

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    pass_rate = passed_count / total

    print(f"Results: {passed_count}/{total} passed ({pass_rate:.0%})")

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed_count,
        "pass_rate": pass_rate,
        "results": results
    }
    with open(EVAL_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return results


if __name__ == "__main__":
    run_evaluation()