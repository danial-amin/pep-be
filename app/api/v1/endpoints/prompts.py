"""
Prompt completion endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.vector_db import vector_db
from app.core.llm_service import llm_service
from app.schemas.persona import PromptCompleteRequest, PromptCompleteResponse

router = APIRouter()


@router.post("/complete", response_model=PromptCompleteResponse)
async def complete_prompt(
    request: PromptCompleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete a prompt using information from processed documents.
    
    - Queries vector database for relevant context
    - Uses LLM to complete the prompt with context
    - Returns completed text
    """
    try:
        # Query vector database for relevant documents
        query_results = vector_db.query_documents(
            query_texts=[request.prompt],
            n_results=5
        )
        
        # Extract relevant document texts
        context_documents = []
        if query_results.get("documents") and len(query_results["documents"]) > 0:
            context_documents = query_results["documents"][0]  # First query result
        
        if not context_documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant context found. Please process documents first."
            )
        
        # Complete prompt using LLM with context
        completed_text = await llm_service.complete_prompt(
            user_prompt=request.prompt,
            context_documents=context_documents,
            max_tokens=request.max_tokens
        )
        
        return PromptCompleteResponse(
            completed_text=completed_text,
            context_used=len(context_documents)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing prompt: {str(e)}"
        )

