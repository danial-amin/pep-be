"""
Utility to create default documents on startup.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document, DocumentType
from app.services.document_service import DocumentService
import logging

logger = logging.getLogger(__name__)


DEFAULT_CONTEXT_DOCUMENT = """
# Default Context Document

This is a default context document that provides general background information for persona generation.

## Purpose
This document serves as a baseline context for understanding user research and persona generation processes.

## Key Areas Covered
- User research methodologies
- Persona development best practices
- User experience design principles
- Market research fundamentals

## Usage
This document is automatically included to provide foundational context. You can upload additional context documents to supplement this information.
"""

DEFAULT_INTERVIEW_DOCUMENT = """
# Default Interview Document

This is a default interview document template.

## Interview Guidelines
- Focus on user needs and pain points
- Explore user behaviors and motivations
- Understand user goals and challenges
- Identify user preferences and expectations

## Sample Interview Questions
1. What are your main goals when using this product/service?
2. What challenges do you face in your daily workflow?
3. How do you currently solve these problems?
4. What would make your experience better?

## Notes
This is a template document. Upload actual interview transcripts to get meaningful persona insights.
"""

DEFAULT_TRANSCRIPT_DOCUMENT = """
# CipherBot Interview Transcripts

This document contains interview transcripts from users interacting with CipherBot, an educational chatbot focused on animal species conservation.

## Interview Session 1 - Research Coordinator
User: "I'm interested to get the prompts from different perspectives, like what the chatbot knows as a biologist and also as the sustainable scenario."
Interviewer: "Can you tell me more about how you would use this in your research?"
User: "I need AI that functions as a specialist partner, not just a general assistant. I often compare complex biological perspectives across different conservation scenarios. I also need to translate my academic research into accessible social media content for LinkedIn."
Interviewer: "What challenges do you face with current AI tools?"
User: "AI tools that provide overly simplified or generic answers to complex scientific queries are frustrating. I also waste time correcting 'hallucinations' in technical data regarding species population."

## Interview Session 2 - Medical Professional
User: "They're harvesting data to manipulate you. I want the big picture—don't ask me questions. Ask me if I have any questions."
Interviewer: "What do you mean by that?"
User: "I prefer high-level summaries and strategic 'big picture' insights over granular details. I have zero patience for conversational filler or systems that demand constant user input without providing immediate, high-value evidence."
Interviewer: "How do you currently use AI tools?"
User: "I use AI as a passive information source rather than an interactive tutor. I strongly prefer text chat to maintain control over the interaction flow. I dislike voice interaction due to perceived privacy risks."

## Interview Session 3 - Economist
User: "I would love to use this for my work... extracting information from a 30-page document which takes two hours and getting a summary instead."
Interviewer: "What type of documents do you work with?"
User: "I analyze extensive policy documents and data sets to improve educational access. I'm a visual learner who thrives on summaries that highlight key takeaways quickly, saving me hours of manual reading."
Interviewer: "What features would be most valuable?"
User: "I need tools that can extract precise, reliable data from long, complex texts. I prefer structured, visual outputs like tables or lists. I also need a seamless handoff between mobile and desktop sessions."

## Interview Session 4 - Student
User: "Personally, I'm not an AI user. I find it hard to use... I wasn't sure on what to write. It would be good to have a tutorial."
Interviewer: "What makes it difficult for you?"
User: "I often feel overwhelmed by the 'blank slate' nature of AI chat interfaces. I find it difficult to know how to start a conversation with a bot. I prefer structured environments like Discord for community support."
Interviewer: "What would help you get started?"
User: "I seek tools that can provide clear, step-by-step tutorials rather than forcing me to guess the right prompts. I learn best through watching examples or following a guided tutorial. I value templates and pre-filled prompt suggestions."

## Interview Session 5 - High School Student
User: "The voice synthesizer itself was a bit slow, so making it faster makes it more human-like. I don't like to talk; it breaks the concentration."
Interviewer: "What's your primary use case?"
User: "I use AI to quickly generate eye-catching conservation posts for my school's eco-club social media. I also use it to find specific facts about endangered species for biology homework."
Interviewer: "What's most important to you?"
User: "Efficiency is my primary metric for success. I have a low tolerance for slow response times or clunky interfaces. I prefer text chat for high-speed interaction and easy multi-tasking. I expect instant responses and minimal latency."

## Key Themes from Transcripts
- Users value specialist-level information over generic responses
- Privacy and data control are important concerns
- Visual learners prefer structured outputs and summaries
- Novice users need guidance and tutorials
- Efficiency and speed are critical for digital natives
- Text-based interaction is preferred over voice for most users
- Users want to extract insights from long documents quickly
"""


async def create_default_documents(session: AsyncSession) -> None:
    """Create default documents if they don't exist."""
    try:
        # Check if default context document exists
        context_result = await session.execute(
            select(Document).where(
                Document.filename == "default_context.md",
                Document.document_type == DocumentType.CONTEXT
            )
        )
        existing_context = context_result.scalar_one_or_none()
        
        if not existing_context:
            logger.info("Creating default context document")
            # Create default context document
            document = await DocumentService.process_document(
                session=session,
                file_path="",  # No file, using text content
                filename="default_context.md",
                document_type=DocumentType.CONTEXT,
                content=DEFAULT_CONTEXT_DOCUMENT
            )
            logger.info(f"Created default context document with ID: {document.id}")
        
        # Check if default interview document exists
        interview_result = await session.execute(
            select(Document).where(
                Document.filename == "default_interview.md",
                Document.document_type == DocumentType.INTERVIEW
            )
        )
        existing_interview = interview_result.scalar_one_or_none()
        
        if not existing_interview:
            logger.info("Creating default interview document")
            # Create default interview document
            document = await DocumentService.process_document(
                session=session,
                file_path="",  # No file, using text content
                filename="default_interview.md",
                document_type=DocumentType.INTERVIEW,
                content=DEFAULT_INTERVIEW_DOCUMENT
            )
            logger.info(f"Created default interview document with ID: {document.id}")
        
        # Check if default transcript document exists
        transcript_result = await session.execute(
            select(Document).where(
                Document.filename == "transcripts-cipherbot.md",
                Document.document_type == DocumentType.INTERVIEW
            )
        )
        existing_transcript = transcript_result.scalar_one_or_none()
        
        if not existing_transcript:
            logger.info("Creating default CipherBot transcript document")
            # Create default transcript document
            document = await DocumentService.process_document(
                session=session,
                file_path="",  # No file, using text content
                filename="transcripts-cipherbot.md",
                document_type=DocumentType.INTERVIEW,
                content=DEFAULT_TRANSCRIPT_DOCUMENT
            )
            logger.info(f"Created default CipherBot transcript document with ID: {document.id}")
        
        await session.commit()
    except Exception as e:
        logger.error(f"Error creating default documents: {e}")
        await session.rollback()

