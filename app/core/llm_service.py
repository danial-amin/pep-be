"""
LLM service for processing documents and generating personas.
"""
from openai import AsyncOpenAI
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from typing import List, Dict, Any, Optional
import json


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
    
    async def process_document(self, document_text: str, document_type: str) -> Dict[str, Any]:
        """Process a document and extract relevant information."""
        prompt = f"""Analyze the following {document_type} document and extract key information.
        
Document:
{document_text}

Provide a structured summary with:
1. Key themes and topics
2. Important details and facts
3. Relevant context for persona generation

Return as JSON format."""
        
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
    
    async def complete_prompt(
        self,
        user_prompt: str,
        context_documents: List[str],
        max_tokens: int = 1000
    ) -> str:
        """Complete a prompt using context from documents."""
        context = "\n\n".join([f"Context {i+1}:\n{doc}" for i, doc in enumerate(context_documents)])
        
        full_prompt = f"""Based on the following context information, complete the user's prompt.

Context Information:
{context}

User Prompt:
{user_prompt}

Provide a comprehensive and accurate response based on the context provided."""
        
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
    
    async def generate_persona_set(
        self,
        interview_documents: List[str],
        context_documents: List[str],
        num_personas: int = 3
    ) -> Dict[str, Any]:
        """Generate initial persona set with demographics."""
        context = "\n\n".join(context_documents)
        interviews = "\n\n".join([f"Interview {i+1}:\n{interview}" for i, interview in enumerate(interview_documents)])
        
        prompt = f"""Based on the following context and interview data, generate {num_personas} distinct personas with basic demographics.

Context Information:
{context}

Interview Data:
{interviews}

Generate {num_personas} personas, each with:
- name
- age
- gender
- location
- occupation
- basic_description
- key_characteristics

Return as JSON with a 'personas' array."""
        
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at creating realistic personas based on research data and interviews."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def expand_persona(self, persona_basic: Dict[str, Any], context_documents: List[str]) -> Dict[str, Any]:
        """Expand a basic persona into a full-fledged persona."""
        context = "\n\n".join(context_documents)
        persona_str = json.dumps(persona_basic, indent=2)
        
        prompt = f"""Expand the following basic persona into a comprehensive, detailed persona profile.

Context Information:
{context}

Basic Persona:
{persona_str}

Create a full persona with:
- personal_background
- demographics (age, gender, location, education, income, etc.)
- psychographics (values, interests, motivations, pain_points)
- behaviors (habits, preferences, decision_making_style)
- goals_and_challenges
- technology_usage
- communication_preferences
- detailed_description

Return as a complete JSON persona object."""
        
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at creating detailed, realistic persona profiles."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        return json.loads(response.choices[0].message.content)
    
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


# Global LLM service instance
llm_service = LLMService()

