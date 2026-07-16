GOLDEN_SET = [
    {
        "question": "What did Jack ignore?",
        "expected_answer_contains": ["Do Not Enter"],
        "should_be_answerable": True,
    },
    {
        "question": "What colors does she like?",
        "expected_answer_contains": ["teal", "sea green"],
        "should_be_answerable": True,
    },
    {
        "question": "Why couldn't she have a relationship with her date?",
        "expected_answer_contains": ["colorblind"],
        "should_be_answerable": True,
    },
    {
        "question": "What was making a statement that couldn't be understood?",
        "expected_answer_contains": ["trees"],
        "should_be_answerable": True,
    },
    {
        "question": "Why did the group blame each other?",
        "expected_answer_contains": ["failed", "result"],
        "should_be_answerable": True,
    },
    {
        "question": "What is the capital of France?",
        "expected_answer_contains": ["don't know", "cannot", "no information"],
        "should_be_answerable": False,
    },
    {
        "question": "What is the best pizza topping?",
        "expected_answer_contains": ["don't know", "cannot", "no information"],
        "should_be_answerable": False,
    },
]