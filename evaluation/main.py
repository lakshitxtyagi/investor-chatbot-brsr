"""
LLM evaluation service for RAG pipeline assessment.
Uses OpenAI API to evaluate answers on Faithfulness, Context Relevance, and Answer Correctness.
"""

import json
import os
from typing import TypedDict, Literal
from openai import OpenAI

from prompts import (
    build_faithfulness_prompt,
    build_context_relevance_prompt,
    build_answer_correctness_prompt,
)


# Type definitions
class EvalInput(TypedDict):
    query: str
    context: str
    answer: str
    eval_type: Literal["faithfulness", "context_relevance", "answer_correctness"]


class EvalResult(TypedDict):
    score: float
    reason: str
    eval_type: str


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def evaluate_rag(input_data: EvalInput) -> EvalResult:
    """
    Evaluate the RAG system response using LLM as a judge.
    
    Args:
        input_data: Dictionary containing query, context, answer, and eval_type
        
    Returns:
        EvalResult with score and reasoning
    """
    eval_type = input_data["eval_type"]
    
    # Build appropriate prompt based on evaluation type
    if eval_type == "faithfulness":
        prompt = build_faithfulness_prompt(
            query=input_data["query"],
            context=input_data["context"],
            answer=input_data["answer"],
        )
    elif eval_type == "context_relevance":
        prompt = build_context_relevance_prompt(
            query=input_data["query"],
            context_chunks=input_data["context"],
        )
    elif eval_type == "answer_correctness":
        prompt = build_answer_correctness_prompt(
            query=input_data["query"],
            answer=input_data["answer"],
        )
    else:
        raise ValueError(f"Unknown evaluation type: {eval_type}")
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # cheap + good enough
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a strict evaluator of RAG systems. Always return valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    
    # Parse response
    response_text = response.choices[0].message.content
    result_json = json.loads(response_text)
    
    return EvalResult(
        score=result_json["score"],
        reason=result_json["reason"],
        eval_type=eval_type,
    )


async def evaluate_faithfulness(
    query: str, context: str, answer: str
) -> EvalResult:
    """
    Evaluate if the answer is strictly supported by the retrieved context.
    
    Args:
        query: The original question
        context: The retrieved context
        answer: The generated answer
        
    Returns:
        EvalResult with faithfulness score
    """
    return await evaluate_rag(
        {
            "query": query,
            "context": context,
            "answer": answer,
            "eval_type": "faithfulness",
        }
    )
    
async def evaluate_context_relevance(query: str, context: str) -> EvalResult:
    """
    Evaluate how relevant the context is to answering the question.
    
    Args:
        query: The original question
        context: The retrieved context chunks
        
    Returns:
        EvalResult with context relevance score
    """
    return await evaluate_rag(
        {
            "query": query,
            "context": context,
            "answer": "",  # Not used for this evaluation
            "eval_type": "context_relevance",
        }
    )


async def evaluate_answer_correctness(query: str, answer: str) -> EvalResult:
    """
    Evaluate whether the answer directly and clearly addresses the question.
    
    Args:
        query: The original question
        answer: The generated answer
        
    Returns:
        EvalResult with answer correctness score
    """
    return await evaluate_rag(
        {
            "query": query,
            "context": "",  # Not used for this evaluation
            "answer": answer,
            "eval_type": "answer_correctness",
        }
    )

