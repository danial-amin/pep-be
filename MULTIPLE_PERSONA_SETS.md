# Loading Multiple Default Persona Sets

## Overview

The system now supports loading multiple default persona sets from different JSON files. This allows you to:
- Organize personas into different sets (e.g., by project, domain, or use case)
- Load specific sets on demand
- Maintain multiple persona libraries

## File Naming Conventions

### Option 1: Named Sets
Name your files with a set identifier:
- `default_personas_set1.json` → Set name: "set1"
- `default_personas_set2.json` → Set name: "set2"
- `default_personas_research.json` → Set name: "research"
- `default_personas_marketing.json` → Set name: "marketing"

### Option 2: Directory Structure
Organize sets in a directory:
```
default_personas/
  ├── set1.json
  ├── set2.json
  ├── research.json
  └── marketing.json
```

### Option 3: Default Set
Keep the original file for backward compatibility:
- `default_personas.json` → Set name: "default"

## API Usage

### 1. List Available Persona Sets

```bash
GET /api/v1/personas/available-persona-sets
```

Response:
```json
{
  "available_sets": [
    {
      "name": "default",
      "path": "/app/default_personas.json",
      "filename": "default_personas.json"
    },
    {
      "name": "set1",
      "path": "/app/default_personas_set1.json",
      "filename": "default_personas_set1.json"
    },
    {
      "name": "set2",
      "path": "/app/default_personas_set2.json",
      "filename": "default_personas_set2.json"
    }
  ],
  "count": 3
}
```

### 2. Load a Specific Set by Name

```bash
POST /api/v1/personas/load-default-personas?set_name=set1
```

Or with a custom persona set name:
```bash
POST /api/v1/personas/load-default-personas?set_name=set1&persona_set_name=Research Personas
```

### 3. Load from Specific File Path

```bash
POST /api/v1/personas/load-default-personas?file_path=/path/to/personas.json
```

### 4. Overwrite Existing Set

```bash
POST /api/v1/personas/load-default-personas?set_name=set1&overwrite=true
```

## Parameters

### Query Parameters

- `set_name` (optional): Name of the set to load (e.g., "set1", "research")
  - Looks for files like `default_personas_{set_name}.json`
  
- `file_path` (optional): Specific file path to load from
  - Takes precedence over `set_name`
  
- `persona_set_name` (optional): Custom name for the persona set in the database
  - If not provided, uses metadata from JSON or generates a name
  
- `overwrite` (optional, default: false): Whether to overwrite existing persona set with same name
  - If false, returns existing set if found
  - If true, deletes existing personas and loads new ones

## Examples

### Example 1: Load Set by Name

```python
# Load "set1" persona set
POST /api/v1/personas/load-default-personas?set_name=set1

# Response: Creates a persona set named "Persona Set Set1" (or from metadata)
```

### Example 2: Load with Custom Name

```python
# Load "research" set with custom database name
POST /api/v1/personas/load-default-personas?set_name=research&persona_set_name=Research Team Personas

# Response: Creates a persona set named "Research Team Personas"
```

### Example 3: Load from Specific File

```python
# Load from absolute path
POST /api/v1/personas/load-default-personas?file_path=/app/data/research_personas.json
```

### Example 4: Overwrite Existing Set

```python
# Load and overwrite existing "set1" set
POST /api/v1/personas/load-default-personas?set_name=set1&overwrite=true
```

## JSON File Structure

Each persona set JSON file should follow this structure:

```json
{
  "metadata": {
    "name": "Optional Set Name",
    "context": "Description of this persona set",
    "version": "1.0"
  },
  "personas": [
    {
      "persona_id": "persona_001",
      "name": "Persona Name",
      "tagline": "Persona tagline",
      "demographics": {
        "age": 30,
        "location": {
          "city": "City",
          "country": "Country"
        },
        "occupation": "Job Title"
      },
      "background": "Background description",
      "goals": ["Goal 1", "Goal 2"],
      "frustrations": ["Frustration 1"],
      "technology_profile": {
        "primary_devices": ["Device 1"],
        "comfort_level": "Advanced"
      },
      "quote": "Persona quote"
    }
  ]
}
```

## File Locations

The system searches for persona set files in these locations (in order):

1. **Root directory**: `{project_root}/default_personas_*.json`
2. **Docker container**: `/app/default_personas_*.json`
3. **Current directory**: `./default_personas_*.json`
4. **Directory structure**: `{project_root}/default_personas/*.json`

## Startup Behavior

On application startup, the system automatically loads the default set (`default_personas.json`) if:
- No "Default Persona Set" exists in the database
- The file is found in standard locations

To load additional sets, use the API endpoint after startup.

## Best Practices

1. **Use Descriptive Set Names**: Use meaningful names like "research", "marketing", "enterprise" instead of generic "set1", "set2"

2. **Include Metadata**: Add metadata to your JSON files for better organization:
   ```json
   {
     "metadata": {
       "name": "Research Team Personas",
       "context": "Personas for research team user studies",
       "version": "1.0",
       "created": "2024-01-01"
     }
   }
   ```

3. **Organize by Use Case**: Group personas by:
   - Project/domain (e.g., "healthcare", "finance")
   - User type (e.g., "enterprise", "consumer")
   - Research phase (e.g., "discovery", "validation")

4. **Version Control**: Keep persona sets in version control for tracking changes

5. **Naming Convention**: Use consistent naming:
   - `default_personas_{domain}.json`
   - `default_personas_{project}.json`
   - `default_personas_{team}.json`

## Migration from Single Set

If you currently have a single `default_personas.json` file:

1. **Keep it as default**: The system will continue to load it automatically
2. **Create new sets**: Add new files like `default_personas_set2.json`
3. **Load on demand**: Use the API to load additional sets when needed

## Error Handling

- If a set is not found, the API returns a 404 with a list of available sets
- If a file is invalid JSON, an error is logged and an empty set is returned
- If a persona set name already exists and `overwrite=false`, the existing set is returned
