"""
Langfuse client for LLM observability and tracking.
"""
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe
from langfuse.openai import openai as langfuse_openai
from app.core.config import settings
from typing import Optional, Dict, Any, List
import logging
import uuid

logger = logging.getLogger(__name__)

# Global Langfuse client instance
_langfuse_client: Optional[Langfuse] = None
_langfuse_enabled: bool = False


def get_langfuse_client() -> Optional[Langfuse]:
    """Get or create Langfuse client instance."""
    global _langfuse_client, _langfuse_enabled
    
    if not settings.LANGFUSE_ENABLED:
        _langfuse_enabled = False
        return None
    
    if _langfuse_client is None:
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                _langfuse_client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                _langfuse_enabled = True
                logger.info("Langfuse client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse client: {e}. Continuing without observability.")
                _langfuse_client = None
                _langfuse_enabled = False
        else:
            logger.warning("Langfuse keys not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable observability.")
            _langfuse_client = None
            _langfuse_enabled = False
    
    return _langfuse_client


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and configured."""
    return _langfuse_enabled and _langfuse_client is not None


def get_openai_client_with_tracing(openai_client):
    """
    Wrap OpenAI client with Langfuse tracing.
    Returns the original client if Langfuse is not enabled.
    """
    if not is_langfuse_enabled():
        return openai_client
    
    try:
        # Use Langfuse's OpenAI wrapper for automatic tracing
        return langfuse_openai
    except Exception as e:
        logger.warning(f"Failed to wrap OpenAI client with Langfuse: {e}")
        return openai_client


def trace_generation(
    name: str,
    model: str,
    input: Any,
    output: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
    level: str = "DEFAULT",
    trace_id: Optional[str] = None,
    parent_observation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """
    Create a trace for an LLM generation.
    
    Returns:
        Observation ID if successful, None otherwise
    """
    if not is_langfuse_enabled():
        return None
    
    client = get_langfuse_client()
    if not client:
        return None
    
    try:
        trace = client.trace(
            name=name,
            id=trace_id or str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        generation = trace.generation(
            name=name,
            model=model,
            input=input,
            output=output,
            metadata=metadata or {},
            level=level,
            parent_observation_id=parent_observation_id
        )
        
        return generation.id
    except Exception as e:
        logger.warning(f"Failed to create Langfuse trace: {e}")
        return None


def trace_span(
    name: str,
    input: Optional[Any] = None,
    output: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    parent_observation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """
    Create a span for tracking operations.
    
    Returns:
        Observation ID if successful, None otherwise
    """
    if not is_langfuse_enabled():
        return None
    
    client = get_langfuse_client()
    if not client:
        return None
    
    try:
        trace = client.trace(
            name=name,
            id=trace_id or str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        span = trace.span(
            name=name,
            input=input,
            output=output,
            metadata=metadata or {},
            parent_observation_id=parent_observation_id
        )
        
        return span.id
    except Exception as e:
        logger.warning(f"Failed to create Langfuse span: {e}")
        return None


def trace_event(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    parent_observation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """
    Create an event for tracking specific occurrences (errors, milestones, etc.).
    
    Returns:
        Observation ID if successful, None otherwise
    """
    if not is_langfuse_enabled():
        return None
    
    client = get_langfuse_client()
    if not client:
        return None
    
    try:
        trace = client.trace(
            name=name,
            id=trace_id or str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        event = trace.event(
            name=name,
            metadata=metadata or {},
            parent_observation_id=parent_observation_id
        )
        
        return event.id
    except Exception as e:
        logger.warning(f"Failed to create Langfuse event: {e}")
        return None


def create_trace(
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None
):
    """
    Create a new trace for tracking a complete operation.
    
    Returns:
        Trace object if successful, None otherwise
    """
    if not is_langfuse_enabled():
        return None
    
    client = get_langfuse_client()
    if not client:
        return None
    
    try:
        trace = client.trace(
            name=name,
            id=trace_id or str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        return trace
    except Exception as e:
        logger.warning(f"Failed to create Langfuse trace: {e}")
        return None


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None
):
    """Score a trace (for feedback/quality metrics)."""
    client = get_langfuse_client()
    if not client:
        return
    
    try:
        client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment
        )
    except Exception as e:
        logger.warning(f"Failed to score Langfuse trace: {e}")
