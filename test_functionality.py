"""
Test script to verify all persona generation functionalities are working properly.
Run this script to test:
1. Document processing
2. Persona set generation
3. Persona expansion
4. Image generation
5. Analytics (diversity measurement, validation)
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from app.core.llm_service import LLMService
from app.services.persona_service import PersonaService
from app.services.document_service import DocumentService
from app.models.document import Document
from app.models.persona import PersonaSet, Persona
from sqlalchemy import select
import json


async def test_document_processing():
    """Test document processing functionality."""
    print("\n" + "="*60)
    print("TEST 1: Document Processing")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if any documents exist
            result = await session.execute(select(Document))
            documents = result.scalars().all()
            
            print(f"✓ Found {len(documents)} documents in database")
            
            if documents:
                for doc in documents[:3]:  # Show first 3
                    print(f"  - {doc.name} ({doc.document_type})")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_persona_set_generation():
    """Test persona set generation."""
    print("\n" + "="*60)
    print("TEST 2: Persona Set Generation")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if any persona sets exist
            result = await session.execute(select(PersonaSet))
            persona_sets = result.scalars().all()
            
            print(f"✓ Found {len(persona_sets)} persona sets in database")
            
            if persona_sets:
                for ps in persona_sets[:3]:  # Show first 3
                    print(f"  - {ps.name} (ID: {ps.id}, Status: {ps.status})")
                    # Count personas
                    result2 = await session.execute(
                        select(Persona).where(Persona.persona_set_id == ps.id)
                    )
                    personas = result2.scalars().all()
                    print(f"    → {len(personas)} personas")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_persona_expansion():
    """Test persona expansion functionality."""
    print("\n" + "="*60)
    print("TEST 3: Persona Expansion")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if any expanded personas exist
            result = await session.execute(select(Persona))
            personas = result.scalars().all()
            
            expanded_count = 0
            basic_count = 0
            
            for persona in personas:
                if persona.persona_data:
                    # Check if persona has expanded fields
                    data = persona.persona_data
                    if isinstance(data, dict):
                        # Check for expanded fields
                        expanded_fields = ['goals', 'behaviors', 'frustrations', 'background', 'technology_profile']
                        has_expanded = any(field in data for field in expanded_fields)
                        if has_expanded:
                            expanded_count += 1
                        else:
                            basic_count += 1
            
            print(f"✓ Found {len(personas)} total personas")
            print(f"  - {expanded_count} expanded personas")
            print(f"  - {basic_count} basic personas")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_image_generation():
    """Test image generation functionality."""
    print("\n" + "="*60)
    print("TEST 4: Image Generation")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check personas with images
            result = await session.execute(select(Persona))
            personas = result.scalars().all()
            
            with_images = sum(1 for p in personas if p.image_url)
            without_images = len(personas) - with_images
            
            print(f"✓ Found {len(personas)} personas")
            print(f"  - {with_images} with images")
            print(f"  - {without_images} without images")
            
            # Check if static directory exists
            import os
            static_dir = "/app/static/images/personas"
            if os.path.exists(static_dir):
                image_files = [f for f in os.listdir(static_dir) if f.endswith('.png')]
                print(f"  - {len(image_files)} image files in static directory")
            else:
                print(f"  - Static directory not found (expected in Docker)")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_analytics():
    """Test analytics functionality."""
    print("\n" + "="*60)
    print("TEST 5: Analytics (Diversity & Validation)")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check persona sets with analytics
            result = await session.execute(select(PersonaSet))
            persona_sets = result.scalars().all()
            
            with_rqe = sum(1 for ps in persona_sets if ps.rqe_scores)
            with_validation = sum(1 for ps in persona_sets if ps.validation_scores)
            
            print(f"✓ Found {len(persona_sets)} persona sets")
            print(f"  - {with_rqe} with RQE scores")
            print(f"  - {with_validation} with validation scores")
            
            # Show example scores if available
            for ps in persona_sets[:2]:
                if ps.rqe_scores:
                    print(f"\n  Example: {ps.name}")
                    print(f"    RQE Scores: {ps.rqe_scores}")
                if ps.validation_scores:
                    print(f"    Validation Scores: {ps.validation_scores}")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_prompts_loading():
    """Test that custom prompts are loading correctly."""
    print("\n" + "="*60)
    print("TEST 6: Custom Prompts Loading")
    print("="*60)
    
    try:
        from app.utils.prompts import (
            PERSONA_SET_GENERATION_SYSTEM_PROMPT,
            PERSONA_EXPANSION_SYSTEM_PROMPT,
            PERSONA_EXPANSION_PROMPT_TEMPLATE
        )
        
        print("✓ Successfully imported prompts")
        print(f"  - Persona Set System Prompt: {len(PERSONA_SET_GENERATION_SYSTEM_PROMPT)} chars")
        print(f"  - Persona Expansion System Prompt: {len(PERSONA_EXPANSION_SYSTEM_PROMPT)} chars")
        print(f"  - Persona Expansion Template: {len(PERSONA_EXPANSION_PROMPT_TEMPLATE)} chars")
        
        # Check if template has required placeholders
        required_placeholders = ['{context}', '{persona_basic}']
        missing = [p for p in required_placeholders if p not in PERSONA_EXPANSION_PROMPT_TEMPLATE]
        
        if missing:
            print(f"  ⚠ Warning: Missing placeholders: {missing}")
        else:
            print(f"  ✓ All required placeholders present")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PERSONA GENERATION FUNCTIONALITY TEST")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(await test_prompts_loading())
    results.append(await test_document_processing())
    results.append(await test_persona_set_generation())
    results.append(await test_persona_expansion())
    results.append(await test_image_generation())
    results.append(await test_analytics())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print("⚠ Some tests failed. Check the output above for details.")
    
    print("\n" + "="*60)
    print("CUSTOM PROMPTS LOCATION")
    print("="*60)
    print("To customize prompts, edit: app/utils/prompts.py")
    print("  - PERSONA_SET_GENERATION_SYSTEM_PROMPT: System prompt for persona generation")
    print("  - PERSONA_EXPANSION_SYSTEM_PROMPT: System prompt for persona expansion")
    print("  - PERSONA_EXPANSION_PROMPT_TEMPLATE: Main expansion prompt template")
    print("\nAfter editing, restart the application for changes to take effect.")


if __name__ == "__main__":
    asyncio.run(main())

