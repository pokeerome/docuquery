import re
from app.query import llm


def parse_judge_response(response_text: str) -> dict:
    score_match = re.search(r"SCORE:\s*([\d.]+)", response_text)
    reason_match = re.search(r"REASON:\s*(.+)", response_text, re.DOTALL)

    score = float(score_match.group(1)) if score_match else None
    reason = reason_match.group(1).strip() if reason_match else "No reason provided"

    return {"score": score, "reason": reason}


def judge_faithfulness(question: str, answer: str, context: str) -> dict:
    judge_prompt = f"""You are evaluating whether an AI-generated answer is faithful to its source context.

Context:
{context}

Question: {question}
Answer: {answer}

Is the answer fully supported by the context, with no invented information not present in the context?
A score of 1.0 means fully supported. A score of 0.0 means the answer contains information not found in the context.

Respond in exactly this format:
SCORE: <a number from 0.0 to 1.0>
REASON: <one sentence explanation>"""

    response = llm.invoke(judge_prompt)
    return parse_judge_response(response.content)


def judge_relevancy(question: str, answer: str) -> dict:
    judge_prompt = f"""You are evaluating whether an AI-generated answer actually addresses the question asked.

Question: {question}
Answer: {answer}

Does the answer directly and relevantly address the question?
A score of 1.0 means fully relevant and on-topic. A score of 0.0 means the answer does not address the question at all.

Respond in exactly this format:
SCORE: <a number from 0.0 to 1.0>
REASON: <one sentence explanation>"""

    response = llm.invoke(judge_prompt)
    return parse_judge_response(response.content)