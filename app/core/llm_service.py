"""
LLM service for processing documents and generating personas.
"""
from openai import AsyncOpenAI
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.utils.token_utils import chunk_text_by_tokens, estimate_tokens
from app.utils.prompts import (
    PERSONA_SET_GENERATION_SYSTEM_PROMPT,
    PERSONA_SET_GENERATION_PROMPT_TEMPLATE,
    PERSONA_SET_GENERATION_INTERVIEWS_ONLY_TEMPLATE,
    PERSONA_SET_GENERATION_CONTEXT_ONLY_TEMPLATE,
    PERSONA_EXPANSION_SYSTEM_PROMPT,
    PERSONA_EXPANSION_PROMPT_TEMPLATE
)
from typing import List, Dict, Any, Optional
import json
import asyncio
import logging
from openai import RateLimitError, APIError

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenAI LLM."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for texts."""
        return await self.embeddings.aembed_documents(texts)
    
    async def create_query_embedding(self, text: str) -> List[float]:
        """Create embedding for a single query text."""
        return await self.embeddings.aembed_query(text)
    
    async def process_document(self, document_text: str, document_type: str) -> Dict[str, Any]:
        """
        Process a document and extract relevant information.
        Handles large documents by processing in chunks.
        """
        # Estimate tokens
        estimated_tokens = estimate_tokens(document_text)
        logger.info(f"Processing document with estimated {estimated_tokens} tokens")
        
        # If document is small enough, process directly
        if estimated_tokens <= settings.MAX_TOKENS_PER_CHUNK:
            return await self._process_document_chunk(document_text, document_type)
        
        # Otherwise, process in chunks
        chunks = chunk_text_by_tokens(
            document_text,
            max_tokens=settings.MAX_TOKENS_PER_CHUNK,
            overlap_tokens=settings.CHUNK_OVERLAP_TOKENS
        )
        
        logger.info(f"Processing document in {len(chunks)} chunks")
        
        # Process chunks sequentially with delays to avoid rate limits
        chunk_results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            try:
                chunk_result = await self._process_document_chunk(chunk, document_type, chunk_index=i+1, total_chunks=len(chunks))
                chunk_results.append(chunk_result)
                
                # Add delay between chunks to avoid rate limits (except for last chunk)
                if i < len(chunks) - 1:
                    await asyncio.sleep(settings.PROCESSING_DELAY_SECONDS)
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                # Continue with other chunks even if one fails
                continue
        
        # Combine results from all chunks
        return self._combine_chunk_results(chunk_results, document_type)
    
    async def _process_document_chunk(
        self,
        chunk_text: str,
        document_type: str,
        chunk_index: int = 1,
        total_chunks: int = 1
    ) -> Dict[str, Any]:
        """Process a single chunk of a document with retry logic for rate limits."""
        if total_chunks > 1:
            prompt = f"""Analyze the following section (part {chunk_index} of {total_chunks}) from a {document_type} document and extract key information.
        
Document Section:
{chunk_text}

Provide a structured summary with:
1. Key themes and topics in this section
2. Important details and facts
3. Relevant context for persona generation

Return as JSON format."""
        else:
            prompt = f"""Analyze the following {document_type} document and extract key information.
        
Document:
{chunk_text}

Provide a structured summary with:
1. Key themes and topics
2. Important details and facts
3. Relevant context for persona generation

Return as JSON format."""
        
        max_retries = 3
        retry_delay = 60  # Wait 60 seconds on rate limit
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing documents and extracting relevant information for persona generation."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                
                return json.loads(response.choices[0].message.content)
            
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit on chunk {chunk_index}, waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Rate limit error after {max_retries} attempts on chunk {chunk_index}")
                    raise Exception(f"Rate limit exceeded after {max_retries} retries. Please try again later.")
            
            except APIError as e:
                logger.error(f"API error processing chunk {chunk_index}: {e}")
                raise
    
    def _combine_chunk_results(
        self,
        chunk_results: List[Dict[str, Any]],
        document_type: str
    ) -> Dict[str, Any]:
        """Combine results from multiple document chunks into a single summary."""
        if not chunk_results:
            return {
                "key_themes": [],
                "important_details": [],
                "relevant_context": "No content extracted from document."
            }
        
        # If only one chunk, return it directly
        if len(chunk_results) == 1:
            return chunk_results[0]
        
        # Combine themes and details from all chunks
        combined = {
            "key_themes": [],
            "important_details": [],
            "relevant_context": ""
        }
        
        # Collect unique themes
        themes_set = set()
        for result in chunk_results:
            if isinstance(result.get("key_themes"), list):
                themes_set.update(result["key_themes"])
            elif isinstance(result.get("themes"), list):
                themes_set.update(result["themes"])
            elif isinstance(result.get("Key themes and topics"), list):
                themes_set.update(result["Key themes and topics"])
        
        combined["key_themes"] = list(themes_set)
        
        # Collect all details
        details_list = []
        for result in chunk_results:
            if isinstance(result.get("important_details"), list):
                details_list.extend(result["important_details"])
            elif isinstance(result.get("details"), list):
                details_list.extend(result["details"])
            elif isinstance(result.get("Important details and facts"), list):
                details_list.extend(result["Important details and facts"])
        
        combined["important_details"] = details_list
        
        # Combine context
        context_parts = []
        for result in chunk_results:
            context = result.get("relevant_context") or result.get("context") or result.get("Relevant context for persona generation") or ""
            if context:
                context_parts.append(context)
        
        combined["relevant_context"] = "\n\n".join(context_parts) if context_parts else "Document processed successfully."
        
        return combined
    
    async def complete_prompt(
        self,
        user_prompt: str,
        context_documents: List[str],
        max_tokens: int = 1000
    ) -> str:
        """Complete a prompt using context from documents."""
        # Limit context size to avoid token limits
        context_parts = []
        total_tokens = estimate_tokens(user_prompt)
        
        for doc in context_documents:
            doc_tokens = estimate_tokens(doc)
            if total_tokens + doc_tokens > settings.MAX_TOKENS_PER_CHUNK:
                # If adding this doc would exceed limit, stop
                break
            context_parts.append(doc)
            total_tokens += doc_tokens
        
        if not context_parts:
            # If even one document is too large, summarize it
            if context_documents:
                context_parts = [await self._summarize_text(context_documents[0])]
        
        context = "\n\n".join([f"Context {i+1}:\n{doc}" for i, doc in enumerate(context_parts)])
        
        full_prompt = f"""Based on the following context information, complete the user's prompt.

Context Information:
{context}

User Prompt:
{user_prompt}

Provide a comprehensive and accurate response based on the context provided."""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides accurate information based on the provided context."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except RateLimitError as e:
            logger.error(f"Rate limit error completing prompt: {e}")
            raise Exception("Rate limit exceeded. Please try again in a moment.")
        except APIError as e:
            logger.error(f"API error completing prompt: {e}")
            raise
    
    async def generate_persona_set(
        self,
        interview_documents: List[str],
        context_documents: List[str],
        num_personas: int = 3,
        context_details: Optional[str] = None,
        interview_topic: Optional[str] = None,
        user_study_design: Optional[str] = None,
        include_ethical_guardrails: bool = True,
        output_format: str = "json",
        has_interviews: bool = True,
        has_context: bool = True
    ) -> Dict[str, Any]:
        """
        Generate initial persona set with advanced configuration options.
        
        Args:
            interview_documents: List of interview document texts
            context_documents: List of context document texts
            num_personas: Number of personas to generate
            context_details: Additional context about research/market/domain
            interview_topic: What the interviews are about
            user_study_design: Description of user study design and methodology
            include_ethical_guardrails: Whether to include ethical considerations
            output_format: Format for persona output (json, profile, chat, etc.)
            has_interviews: Whether interview documents are available
            has_context: Whether context documents are available
        """
        # Determine which prompt template to use based on available data
        if has_interviews and has_context:
            # Both interviews and context available - use standard template
            context = "\n\n".join(context_documents) if context_documents else ""
            interviews = "\n\n".join([f"Interview {i+1}:\n{interview}" for i, interview in enumerate(interview_documents)])
            prompt_template = PERSONA_SET_GENERATION_PROMPT_TEMPLATE
            full_text = f"Context Information:\n{context}\n\nInterview Data:\n{interviews}"
        elif has_interviews and not has_context:
            # Only interviews available
            interviews = "\n\n".join([f"Interview {i+1}:\n{interview}" for i, interview in enumerate(interview_documents)])
            prompt_template = PERSONA_SET_GENERATION_INTERVIEWS_ONLY_TEMPLATE
            context = ""  # Empty for template
            full_text = f"Interview Data:\n{interviews}"
        elif has_context and not has_interviews:
            # Only context available
            context = "\n\n".join(context_documents) if context_documents else ""
            prompt_template = PERSONA_SET_GENERATION_CONTEXT_ONLY_TEMPLATE
            interviews = ""  # Empty for template
            full_text = f"Context Information:\n{context}"
        else:
            raise ValueError("At least one of interview_documents or context_documents must be provided")
        
        estimated_tokens = estimate_tokens(full_text)
        
        # If too large, summarize documents first
        if estimated_tokens > settings.MAX_TOKENS_PER_CHUNK:
            logger.info(f"Input too large ({estimated_tokens} tokens), summarizing documents first")
            
            # Summarize context documents if available
            if has_context and context_documents:
                summarized_contexts = []
                for doc in context_documents:
                    if estimate_tokens(doc) > settings.MAX_TOKENS_PER_CHUNK:
                        # Summarize large context documents
                        summary = await self._summarize_text(doc)
                        summarized_contexts.append(summary)
                    else:
                        summarized_contexts.append(doc)
                context = "\n\n".join(summarized_contexts)
            
            # Summarize interview documents if available
            if has_interviews and interview_documents:
                summarized_interviews = []
                for doc in interview_documents:
                    if estimate_tokens(doc) > settings.MAX_TOKENS_PER_CHUNK:
                        summary = await self._summarize_text(doc)
                        summarized_interviews.append(summary)
                    else:
                        summarized_interviews.append(doc)
                interviews = "\n\n".join([f"Interview {i+1}:\n{interview}" for i, interview in enumerate(summarized_interviews)])
        
        # Build sections for the customizable prompt template
        additional_context_section = ""
        if context_details:
            additional_context_section = f"\n\nADDITIONAL CONTEXT:\n{context_details}"
        
        interview_topic_section = ""
        if interview_topic:
            interview_topic_section = f"\n\nINTERVIEW TOPIC:\nThe interviews focus on: {interview_topic}"
        
        user_study_design_section = ""
        if user_study_design:
            user_study_design_section = f"\n\nUSER STUDY DESIGN:\n{user_study_design}"
        
        # Get format instructions
        format_instructions = self._get_format_instructions(output_format, num_personas)
        
        # Build ethical guardrails section
        ethical_guardrails_section = ""
        if include_ethical_guardrails:
            ethical_guardrails_section = """\n\nETHICAL AND FAIRNESS CONSIDERATIONS:
Please ensure personas are:
- Representative and diverse (avoid stereotypes)
- Inclusive of different backgrounds, abilities, and perspectives
- Free from bias based on race, gender, age, or other protected characteristics
- Realistic and based on actual data patterns
- Respectful and ethical in representation
- Balanced in representation across different user segments"""
        
        # Use appropriate prompt template based on available data
        prompt = prompt_template.format(
            num_personas=num_personas,
            context=context,
            interviews=interviews,
            additional_context_section=additional_context_section,
            interview_topic_section=interview_topic_section,
            user_study_design_section=user_study_design_section,
            format_instructions=format_instructions,
            ethical_guardrails_section=ethical_guardrails_section
        )
        
        try:
            # Determine response format based on output_format
            response_format = {"type": "json_object"} if output_format == "json" else None
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": PERSONA_SET_GENERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_format,
                temperature=0.8
            )
            
            # Parse response based on format
            if output_format == "json":
                return json.loads(response.choices[0].message.content)
            else:
                # For non-JSON formats, return content in "personas" field for consistency
                # The content will be the formatted text from LLM
                return {
                    "personas": response.choices[0].message.content,
                    "format": output_format,
                    "description": f"Personas generated in {output_format} format"
                }
        except Exception as e:
            logger.error(f"Error generating persona set: {e}")
            raise
    
    def _get_format_instructions(self, output_format: str, num_personas: int) -> str:
        """Get format-specific instructions for persona generation."""
        format_guides = {
            "json": f"""Return as JSON with a 'personas' array. Each persona should have:
- name
- age
- gender
- location
- occupation
- basic_description
- key_characteristics""",
            
            "profile": f"""Generate {num_personas} detailed persona profiles. Each profile should include:
- Name and photo description
- Demographics (age, gender, location, occupation)
- Background and context
- Goals and motivations
- Pain points and challenges
- Behaviors and preferences
- Technology usage
- Quotes or key statements
Format as narrative profiles with rich detail.""",
            
            "chat": f"""Generate {num_personas} personas in a conversational format. Each persona should be presented as:
- A dialogue or interview-style format
- Natural language descriptions
- Conversational tone
- Include direct quotes and speaking style
Format as if having a conversation with each persona.""",
            
            "proto": f"""Generate {num_personas} proto-personas (quick, hypothesis-based personas). Each should include:
- Name
- Key characteristics (3-5 bullet points)
- Primary goal
- Main pain point
- Quick sketch/description
Format as concise, actionable proto-personas.""",
            
            "adhoc": f"""Generate {num_personas} ad-hoc personas (informal, quick personas). Each should include:
- Name and basic info
- Key traits (2-3 sentences)
- Primary use case
- Quick insights
Format as brief, informal persona descriptions.""",
            
            "engaging": f"""Generate {num_personas} engaging, story-driven personas. Each should include:
- Compelling narrative
- Personal story and background
- Emotional journey
- Relatable scenarios
- Vivid descriptions
Format as engaging stories that bring personas to life.""",
            
            "goal_based": f"""Generate {num_personas} goal-based personas. Each should focus on:
- Primary goals and objectives
- Secondary goals
- Success metrics
- Goal-related behaviors
- Goal-driven decision making
Format emphasizing goals and motivations.""",
            
            "role_based": f"""Generate {num_personas} role-based personas. Each should emphasize:
- Professional role and responsibilities
- Role-specific needs
- Work context and environment
- Role-related challenges
- Role-based decision making
Format emphasizing professional roles and contexts.""",
            
            "interactive": f"""Generate {num_personas} interactive personas. Each should include:
- Dynamic characteristics
- Scenario-based descriptions
- Decision trees or paths
- Interactive elements
- Conditional behaviors
Format as personas that can be used in interactive scenarios or simulations."""
        }
        
        return format_guides.get(output_format.lower(), format_guides["json"])
    
    async def expand_persona(self, persona_basic: Dict[str, Any], context_documents: List[str]) -> Dict[str, Any]:
        """Expand a basic persona into a full-fledged persona."""
        # Combine context and check size
        context = "\n\n".join(context_documents)
        persona_str = json.dumps(persona_basic, indent=2)
        
        full_text = f"Context Information:\n{context}\n\nBasic Persona:\n{persona_str}"
        estimated_tokens = estimate_tokens(full_text)
        
        # If too large, summarize context first
        if estimated_tokens > settings.MAX_TOKENS_PER_CHUNK:
            logger.info(f"Input too large ({estimated_tokens} tokens), summarizing context")
            summarized_contexts = []
            for doc in context_documents:
                if estimate_tokens(doc) > settings.MAX_TOKENS_PER_CHUNK:
                    summary = await self._summarize_text(doc)
                    summarized_contexts.append(summary)
                else:
                    summarized_contexts.append(doc)
            context = "\n\n".join(summarized_contexts)
        
        # Use customizable prompt template
        prompt = PERSONA_EXPANSION_PROMPT_TEMPLATE.format(
            context=context,
            persona_basic=persona_str
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": PERSONA_EXPANSION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error expanding persona: {e}")
            raise
    
    async def generate_persona_image_prompt(self, persona: Dict[str, Any]) -> str:
        """Generate an image prompt for a persona."""
        prompt = f"""Create a detailed image generation prompt for this persona:

{json.dumps(persona, indent=2)}

Generate a descriptive prompt that captures:
- Physical appearance
- Setting/environment
- Style and mood
- Professional context if relevant

Return only the image prompt text, no JSON."""
        
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You create detailed image generation prompts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )
        
        return response.choices[0].message.content
    
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        """Generate an image using DALL-E."""
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        
        return response.data[0].url
    
    async def _summarize_text(self, text: str) -> str:
        """Summarize a large text to reduce token usage."""
        chunks = chunk_text_by_tokens(
            text,
            max_tokens=settings.MAX_TOKENS_PER_CHUNK,
            overlap_tokens=settings.CHUNK_OVERLAP_TOKENS
        )
        
        if len(chunks) == 1:
            # Single chunk, summarize directly
            prompt = f"""Summarize the following text, focusing on key points relevant for persona generation:

{chunks[0]}

Provide a concise summary."""
        else:
            # Multiple chunks, summarize each then combine
            summaries = []
            for i, chunk in enumerate(chunks):
                prompt = f"""Summarize the following section (part {i+1} of {len(chunks)}), focusing on key points:

{chunk}

Provide a concise summary."""
                
                response = await self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert at summarizing documents."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                summaries.append(response.choices[0].message.content)
                
                # Add delay between summaries
                if i < len(chunks) - 1:
                    await asyncio.sleep(settings.PROCESSING_DELAY_SECONDS)
            
            # Combine summaries
            combined = "\n\n".join(summaries)
            return combined
        
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at summarizing documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        return response.choices[0].message.content


# Global LLM service instance
llm_service = LLMService()

