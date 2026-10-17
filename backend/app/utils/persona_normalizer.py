"""
Persona structure normalizer.

This module provides functions to normalize persona structures to a standard nested format.
All personas should follow this structure for consistency.
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def normalize_persona_to_nested(persona_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a persona to the standard nested structure.
    
    Standard nested structure:
    {
        "persona_id": str (optional),
        "name": str,
        "tagline": str (optional),
        "demographics": {
            "age": int,
            "gender": str,
            "location": str | {city: str, country: str},
            "occupation": str,
            "education": str (optional),
            "nationality": str (optional),
            "education_level": str (optional),
            "income_bracket": str (optional),
            "relationship_status": str (optional)
        },
        "background": str,
        "goals": List[str],
        "frustrations": List[str],
        "motivations": List[str] (optional),
        "behaviors": str (optional),
        "technology_profile": {
            "primary_devices": List[str],
            "comfort_level": str,
            "software_used": List[str],
            "interaction_preferences": List[str],
            "accessibility_needs": List[str]
        } (optional),
        "quote": str (optional),
        "quotes": List[str] (optional),
        "other_information": str (optional)
    }
    
    Args:
        persona_data: Persona data in any format (flat or nested)
        
    Returns:
        Normalized persona data in standard nested structure
    """
    normalized = {}
    
    # Handle persona_id
    normalized["persona_id"] = persona_data.get("persona_id")
    
    # Handle name
    normalized["name"] = persona_data.get("name", "Unknown Persona")
    
    # Handle tagline/role
    normalized["tagline"] = persona_data.get("tagline") or persona_data.get("role")
    
    # Build demographics object
    demographics = {}
    
    # Age
    if "age" in persona_data:
        demographics["age"] = persona_data["age"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["age"] = persona_data["demographics"].get("age")
    
    # Gender
    if "gender" in persona_data:
        demographics["gender"] = persona_data["gender"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["gender"] = persona_data["demographics"].get("gender")
    
    # Location
    if "location" in persona_data:
        demographics["location"] = persona_data["location"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["location"] = persona_data["demographics"].get("location")
    elif "nationality" in persona_data:
        # Use nationality as location if location not available
        demographics["location"] = persona_data["nationality"]
    
    # Occupation
    if "occupation" in persona_data:
        demographics["occupation"] = persona_data["occupation"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["occupation"] = persona_data["demographics"].get("occupation")
    
    # Education
    if "education" in persona_data:
        demographics["education"] = persona_data["education"]
    elif "education_level" in persona_data:
        demographics["education"] = persona_data["education_level"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["education"] = persona_data["demographics"].get("education") or persona_data["demographics"].get("education_level")
    
    # Nationality
    if "nationality" in persona_data:
        demographics["nationality"] = persona_data["nationality"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["nationality"] = persona_data["demographics"].get("nationality")
    
    # Income bracket
    if "income_bracket" in persona_data:
        demographics["income_bracket"] = persona_data["income_bracket"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["income_bracket"] = persona_data["demographics"].get("income_bracket")
    
    # Relationship status
    if "relationship_status" in persona_data:
        demographics["relationship_status"] = persona_data["relationship_status"]
    elif "demographics" in persona_data and isinstance(persona_data["demographics"], dict):
        demographics["relationship_status"] = persona_data["demographics"].get("relationship_status")
    
    normalized["demographics"] = demographics
    
    # Background
    normalized["background"] = (
        persona_data.get("background") or
        persona_data.get("detailed_description") or
        persona_data.get("personal_background") or
        persona_data.get("background_and_personal_history") or
        persona_data.get("other_information") or
        persona_data.get("basic_description") or
        ""
    )
    
    # Goals - convert to array
    goals = []
    if "goals" in persona_data:
        if isinstance(persona_data["goals"], list):
            goals = persona_data["goals"]
        elif isinstance(persona_data["goals"], str):
            # Split by sentences or newlines if it's a string
            goals = [g.strip() for g in persona_data["goals"].split("\n") if g.strip()]
            if len(goals) == 1:
                # If it's one long string, try splitting by periods
                goals = [g.strip() for g in persona_data["goals"].split(".") if g.strip() and len(g.strip()) > 10]
    elif "goals_and_motivations" in persona_data and isinstance(persona_data["goals_and_motivations"], dict):
        goals_data = persona_data["goals_and_motivations"].get("goals")
        if isinstance(goals_data, list):
            goals = goals_data
        elif isinstance(goals_data, str):
            goals = [g.strip() for g in goals_data.split("\n") if g.strip()]
    
    normalized["goals"] = goals if goals else []
    
    # Frustrations - convert to array
    frustrations = []
    if "frustrations" in persona_data:
        if isinstance(persona_data["frustrations"], list):
            frustrations = persona_data["frustrations"]
        elif isinstance(persona_data["frustrations"], str):
            frustrations = [f.strip() for f in persona_data["frustrations"].split("\n") if f.strip()]
    elif "pain_points" in persona_data:
        if isinstance(persona_data["pain_points"], list):
            frustrations = persona_data["pain_points"]
        elif isinstance(persona_data["pain_points"], str):
            frustrations = [f.strip() for f in persona_data["pain_points"].split("\n") if f.strip()]
    elif "pain_points_and_frustrations" in persona_data:
        if isinstance(persona_data["pain_points_and_frustrations"], list):
            frustrations = persona_data["pain_points_and_frustrations"]
        elif isinstance(persona_data["pain_points_and_frustrations"], str):
            frustrations = [f.strip() for f in persona_data["pain_points_and_frustrations"].split("\n") if f.strip()]
    
    normalized["frustrations"] = frustrations if frustrations else []
    
    # Motivations - convert to array
    motivations = []
    if "motivations" in persona_data:
        if isinstance(persona_data["motivations"], list):
            motivations = persona_data["motivations"]
        elif isinstance(persona_data["motivations"], str):
            motivations = [m.strip() for m in persona_data["motivations"].split("\n") if m.strip()]
    elif "goals_and_motivations" in persona_data and isinstance(persona_data["goals_and_motivations"], dict):
        motivations_data = persona_data["goals_and_motivations"].get("motivations")
        if isinstance(motivations_data, list):
            motivations = motivations_data
        elif isinstance(motivations_data, str):
            motivations = [m.strip() for m in motivations_data.split("\n") if m.strip()]
    
    if motivations:
        normalized["motivations"] = motivations
    
    # Behaviors
    if "behaviors" in persona_data:
        normalized["behaviors"] = persona_data["behaviors"]
    elif "behaviors_and_preferences" in persona_data:
        normalized["behaviors"] = persona_data["behaviors_and_preferences"]
    
    # Technology profile
    if "technology_profile" in persona_data and isinstance(persona_data["technology_profile"], dict):
        normalized["technology_profile"] = persona_data["technology_profile"]
    elif "technology_usage" in persona_data or "digital_literacy" in persona_data:
        # Build technology profile from flat fields
        tech_profile = {}
        if "technology_usage" in persona_data:
            tech_profile["primary_devices"] = (
                persona_data["technology_usage"] if isinstance(persona_data["technology_usage"], list)
                else [persona_data["technology_usage"]]
            )
        if "digital_literacy" in persona_data:
            tech_profile["comfort_level"] = persona_data["digital_literacy"]
        if tech_profile:
            normalized["technology_profile"] = tech_profile
    
    # Quote/Quotes
    if "quotes" in persona_data and isinstance(persona_data["quotes"], list):
        normalized["quotes"] = persona_data["quotes"]
    elif "quote" in persona_data:
        normalized["quote"] = persona_data["quote"]
    
    # Other information
    if "other_information" in persona_data:
        normalized["other_information"] = persona_data["other_information"]

    # Exploratory cluster personas leave these empty on purpose.
    # Preserve them so a later load does not invent an objective or a segment.
    if "objective" in persona_data:
        normalized["objective"] = persona_data["objective"]
    if "segment_name" in persona_data:
        normalized["segment_name"] = persona_data["segment_name"]
    if "k_selected" in persona_data:
        normalized["k_selected"] = persona_data["k_selected"]
    if persona_data.get("image_prompt"):
        normalized["image_prompt"] = persona_data["image_prompt"]
    if persona_data.get("basic_description"):
        normalized["basic_description"] = persona_data["basic_description"]

    # Conduct personas carry measured account patterns. Keep those fields.
    for key in (
        "anthropomorphized",
        "persona_kind",
        "conduct_label",
        "unit",
        "group_id",
        "month",
        "measured_attributes",
        "rules",
        "observed_excerpts",
        "unknowns",
        "narrative_template",
        "source_narrative",
    ):
        if key in persona_data:
            normalized[key] = persona_data[key]

    if is_nonanthropomorphized(persona_data):
        normalized["anthropomorphized"] = False
        normalized["demographics"] = {}
        normalized.pop("motivations", None)
        return normalized

    # Social media usage
    if "social_media_usage" in persona_data:
        if "demographics" not in normalized:
            normalized["demographics"] = {}
        normalized["demographics"]["social_media_usage"] = persona_data["social_media_usage"]

    return normalized


_DEMOGRAPHIC_FIELDS = (
    "age",
    "gender",
    "location",
    "occupation",
    "education",
    "education_level",
    "nationality",
    "income_bracket",
    "relationship_status",
)


def is_nonanthropomorphized(persona_data: Optional[Dict[str, Any]]) -> bool:
    """True when this persona is an observed pattern and must not be given a person.

    Demographic fields stay empty. Goals, motives, and a first-person voice are not filled in.
    """
    if not isinstance(persona_data, dict):
        return False
    if persona_data.get("anthropomorphized") is False:
        return True
    kind = str(persona_data.get("persona_kind") or "").strip().lower().replace("-", "_")
    return kind in {"conduct", "non_anthropomorphized"}


def demographics_not_applicable(persona_data: Optional[Dict[str, Any]]) -> bool:
    """True when demographic fields name an agent, are empty on purpose, or are not applicable.

    Either case is a non-human subject, so image generation must not invent a body.
    """
    if not isinstance(persona_data, dict):
        return False
    if is_nonanthropomorphized(persona_data):
        return True
    demo = persona_data.get("demographics")
    if not isinstance(demo, dict) or not demo:
        return False
    markers = {"not applicable", "n/a", "na", "none", "", "agent"}
    present = [field for field in _DEMOGRAPHIC_FIELDS if field in demo and demo[field] is not None]
    if not present:
        return False
    return all(str(demo[field]).strip().lower() in markers for field in present)


def normalize_persona_set(personas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize a list of personas to the standard nested structure.
    
    Args:
        personas: List of persona data dictionaries
        
    Returns:
        List of normalized persona data dictionaries
    """
    return [normalize_persona_to_nested(persona) for persona in personas]
