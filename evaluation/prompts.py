"""
Evaluation prompts for RAG pipeline assessment using LLM as a judge.
Evaluates three key metrics: Faithfulness, Context Relevance, and Answer Correctness.
"""


def build_faithfulness_prompt(query: str, context: str, answer: str) -> str:
    """
    Build a prompt to evaluate if the answer is strictly supported by the retrieved context.
    
    Args:
        query: The original question/query
        context: The retrieved context chunks
        answer: The generated answer
        
    Returns:
        A formatted prompt string for faithfulness evaluation
    """
    prompt = f"""You are an evaluator.

Given:
Question: {query}
Context: {context}
Answer: {answer}

Evaluate whether the answer is fully supported by the context.

Instructions:
- Mark any claim not present in the context as unsupported.
- If even one major claim is unsupported → penalize score.

Return JSON:
{{
  "score": float (0 to 1),
  "reason": "short explanation"
}}"""
    return prompt


