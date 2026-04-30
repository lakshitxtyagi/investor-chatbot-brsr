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

```
def build_context_relevance_prompt(query: str, context_chunks: str) -> str:
    """
    Build a prompt to evaluate how relevant the context is to answering the question.
    
    Args:
        query: The original question/query
        context_chunks: The retrieved context chunks
        
    Returns:
        A formatted prompt string for context relevance evaluation
    """
    prompt = f"""You are an evaluator.

Given:
Question: {query}
Context: {context_chunks}

Evaluate how relevant the context is to answering the question.

Consider:
- Does it contain useful information?
- Is it noisy or unrelated?

Return JSON:
{{
  "score": float (0 to 1),
  "reason": "short explanation"
}}"""
    return prompt


def build_answer_correctness_prompt(query: str, answer: str) -> str:
    """
    Build a prompt to evaluate whether the answer directly and clearly addresses the question.
    
    Args:
        query: The original question/query
        answer: The generated answer
        
    Returns:
        A formatted prompt string for answer correctness evaluation
    """
    prompt = f"""You are an evaluator.

Given:
Question: {query}
Answer: {answer}

Evaluate whether the answer directly and clearly addresses the question.

Return JSON:
{{
  "score": float (0 to 1),
  "reason": "short explanation"
}}"""
    return prompt
```
