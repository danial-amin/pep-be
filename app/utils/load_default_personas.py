"""
Utility to load default personas from JSON file(s).
Supports multiple persona sets from different files.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import glob

logger = logging.getLogger(__name__)


def load_default_personas(file_path: Optional[str] = None, set_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Load default personas from JSON file.
    
    Args:
        file_path: Optional specific file path to load. If None, tries default locations.
        set_name: Optional set name to look for (e.g., "set1", "set2"). 
                  Looks for files like "default_personas_set1.json"
    
    Returns:
        Dictionary with personas and metadata
    """
    # If specific file path provided, use it
    if file_path:
        json_path = Path(file_path)
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    # If data is a list directly, wrap it
                    data = {"personas": data, "metadata": {}}
                elif isinstance(data, dict):
                    if "personas" in data:
                        # Already has personas key, ensure metadata exists
                        if "metadata" not in data:
                            data["metadata"] = {}
                    elif any(key in data for key in ["name", "persona_id"]):
                        # Single persona object, wrap in array
                        data = {"personas": [data], "metadata": {}}
                    else:
                        logger.warning(f"Unknown JSON structure in {json_path}, expected 'personas' key or array")
                        return {"personas": [], "metadata": {}}
                else:
                    logger.warning(f"Unexpected data type in {json_path}: {type(data)}")
                    return {"personas": [], "metadata": {}}
                
                logger.info(f"Loaded {len(data.get('personas', []))} personas from {json_path}")
                return data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Error loading personas from {json_path}: {e}")
                return {"personas": [], "metadata": {}}
        else:
            logger.warning(f"File not found: {json_path}")
            return {"personas": [], "metadata": {}}
    
    # If set_name provided, look for specific set file
    if set_name:
        possible_paths = [
            # Try default_personas_{name}.json pattern
            Path(__file__).parent.parent.parent / f"default_personas_{set_name}.json",
            Path("/app") / f"default_personas_{set_name}.json",
            # Try personas_{name}.json pattern (alternative naming)
            Path(__file__).parent.parent.parent / "default_personas" / f"personas_{set_name}.json",
            Path("/app") / "default_personas" / f"personas_{set_name}.json",
            # Try {name}.json in default_personas directory
            Path(__file__).parent.parent.parent / "default_personas" / f"{set_name}.json",
            Path("/app") / "default_personas" / f"{set_name}.json",
            # Try in current directory
            Path("default_personas") / f"{set_name}.json",
            Path(f"default_personas_{set_name}.json"),
        ]
        
        logger.info(f"Looking for persona set '{set_name}' in {len(possible_paths)} possible paths")
        for json_path in possible_paths:
            try:
                if json_path.exists():
                    logger.info(f"Attempting to load persona set from: {json_path}")
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    logger.debug(f"Raw data type: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                    
                    # Handle different JSON structures
                    if isinstance(data, list):
                        # Data is a list of personas directly
                        data = {"personas": data, "metadata": {}}
                    elif isinstance(data, dict):
                        if "personas" in data:
                            # Already has personas key, ensure metadata exists
                            if "metadata" not in data:
                                data["metadata"] = {}
                        elif any(key in data for key in ["name", "persona_id"]):
                            # Single persona object, wrap in array
                            data = {"personas": [data], "metadata": {}}
                        else:
                            logger.warning(f"Unknown JSON structure in {json_path}. Data keys: {list(data.keys())}")
                            continue
                    else:
                        logger.warning(f"Unexpected data type in {json_path}: {type(data)}")
                        continue
                    
                    personas_count = len(data.get('personas', []))
                    logger.info(f"Loaded {personas_count} personas from set '{set_name}' at {json_path}")
                    
                    if personas_count == 0:
                        logger.warning(f"No personas found in {json_path}. Data structure: {list(data.keys())}")
                        continue
                    
                    return data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.warning(f"Error loading {json_path}: {e}", exc_info=True)
                continue
        
        logger.warning(f"Persona set '{set_name}' not found. Tried paths: {possible_paths}")
        return {"personas": [], "metadata": {}}
    
    # Default: Try standard default_personas.json locations
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
                
                # Handle different JSON structures
                if isinstance(data, list):
                    # Data is a list of personas directly
                    data = {"personas": data, "metadata": {}}
                elif isinstance(data, dict):
                    if "personas" in data:
                        # Already has personas key, ensure metadata exists
                        if "metadata" not in data:
                            data["metadata"] = {}
                    elif any(key in data for key in ["name", "persona_id"]):
                        # Single persona object, wrap in array
                        data = {"personas": [data], "metadata": {}}
                    else:
                        logger.warning(f"Unknown JSON structure in {json_path}. Data keys: {list(data.keys())}")
                        continue
                else:
                    logger.warning(f"Unexpected data type in {json_path}: {type(data)}")
                    continue
                
                personas_count = len(data.get('personas', []))
                logger.info(f"Loaded {personas_count} default personas from {json_path}")
                
                if personas_count == 0:
                    logger.warning(f"No personas found in {json_path}")
                    continue
                
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading {json_path}: {e}")
            continue
    
    # If none found, log warning and return empty
    logger.warning(f"Default personas file not found. Tried paths: {possible_paths}")
    return {"personas": [], "metadata": {}}


def list_available_persona_sets() -> List[Dict[str, str]]:
    """
    List all available persona set files.
    
    Returns:
        List of dictionaries with 'name' and 'path' for each available set
    """
    sets = []
    
    # Check root directory
    root_dir = Path(__file__).parent.parent.parent
    docker_dir = Path("/app")
    current_dir = Path(".")
    
    search_dirs = [root_dir, docker_dir, current_dir]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        # Look for default_personas*.json files
        pattern = str(search_dir / "default_personas*.json")
        for file_path in glob.glob(pattern):
            path = Path(file_path)
            # Extract set name from filename
            if path.name == "default_personas.json":
                set_name = "default"
            else:
                # Extract name from default_personas_<name>.json
                name_part = path.stem.replace("default_personas_", "")
                set_name = name_part if name_part else "default"
            
            sets.append({
                "name": set_name,
                "path": str(path),
                "filename": path.name
            })
        
        # Also check for directory structure: default_personas/*.json
        persona_dir = search_dir / "default_personas"
        if persona_dir.exists() and persona_dir.is_dir():
            for json_file in persona_dir.glob("*.json"):
                # Extract set name from filename
                filename = json_file.stem
                # Handle personas_{name}.json pattern
                if filename.startswith("personas_"):
                    set_name = filename.replace("personas_", "")
                else:
                    set_name = filename
                
                sets.append({
                    "name": set_name,
                    "path": str(json_file),
                    "filename": json_file.name
                })
    
    # Remove duplicates (same path)
    seen_paths = set()
    unique_sets = []
    for s in sets:
        if s["path"] not in seen_paths:
            seen_paths.add(s["path"])
            unique_sets.append(s)
    
    return unique_sets


def convert_persona_to_db_format(persona_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert persona from JSON format to database format.
    
    This function normalizes all personas to the standard nested structure
    for consistency across all persona sets.
    """
    from app.utils.persona_normalizer import normalize_persona_to_nested
    # Normalize to standard nested structure
    return normalize_persona_to_nested(persona_data)

