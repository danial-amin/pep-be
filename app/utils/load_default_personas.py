"""
Utility to load default personas from JSON file.
"""
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_default_personas() -> Dict[str, Any]:
    """Load default personas from JSON file."""
    # Try multiple possible locations
    possible_paths = [
        Path(__file__).parent.parent.parent / "default_personas.json",  # Root directory
        Path("/app/default_personas.json"),  # Docker container path
        Path("default_personas.json"),  # Current working directory
    ]
    
    for json_path in possible_paths:
        try:
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data.get('personas', []))} default personas from {json_path}")
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            continue
    
    # If none found, log warning and return empty
    logger.warning(f"Default personas file not found. Tried paths: {possible_paths}")
    return {"personas": [], "metadata": {}}


def convert_persona_to_db_format(persona_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert persona from JSON format to database format."""
    return {
        "name": persona_data.get("name", "Unknown"),
        "age": persona_data.get("demographics", {}).get("age"),
        "gender": None,  # Not in JSON format
        "location": f"{persona_data.get('demographics', {}).get('location', {}).get('city', '')}, {persona_data.get('demographics', {}).get('location', {}).get('country', '')}",
        "occupation": persona_data.get("demographics", {}).get("occupation"),
        "basic_description": persona_data.get("tagline", ""),
        "detailed_description": persona_data.get("background", ""),
        "goals": persona_data.get("goals", []),
        "frustrations": persona_data.get("frustrations", []),
        "technology_profile": persona_data.get("technology_profile", {}),
        "quote": persona_data.get("quote", ""),
        "persona_id": persona_data.get("persona_id"),
        "demographics": persona_data.get("demographics", {}),
        # Keep all original data
        "original_data": persona_data
    }

