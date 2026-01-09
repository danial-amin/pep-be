# Loading Multiple Persona Sets - Visibility Guide

## Overview

When you load multiple default persona sets, **each set appears as a separate, distinct persona set** in the system. They are fully independent and visible as individual entries.

## How Sets Appear

### In the Database

Each loaded persona set creates a separate `PersonaSet` record with:
- **Unique ID**: Each set gets its own database ID
- **Unique Name**: Each set has a distinct name
- **Description**: Includes source information (which file it came from)
- **Separate Personas**: Each set contains its own personas

### In the API

**Get All Sets:**
```bash
GET /api/v1/personas/sets
```

Response shows all sets as separate entries:
```json
[
  {
    "id": 1,
    "name": "Default Persona Set",
    "description": "Default personas loaded from JSON",
    "personas": [...],
    "created_at": "2024-01-01T10:00:00Z"
  },
  {
    "id": 2,
    "name": "Set 1 Persona Set",
    "description": "Loaded from set: set1 | File: default_personas_set1.json",
    "personas": [...],
    "created_at": "2024-01-01T11:00:00Z"
  },
  {
    "id": 3,
    "name": "Research Persona Set",
    "description": "Research team personas | Loaded from set: research",
    "personas": [...],
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### In the Frontend

Each persona set appears as a **separate card/entry** in:
- **Personas Page**: Shows all sets in a list, each with its own name and persona count
- **Reports Page**: Each set can be selected individually for analytics
- **Persona Detail Page**: Navigate between sets and their personas

## Example: Loading Multiple Sets

### Step 1: Load First Set
```bash
POST /api/v1/personas/load-default-personas?set_name=set1&persona_set_name=Research Team Personas
```

**Result**: Creates Persona Set #1 named "Research Team Personas"

### Step 2: Load Second Set
```bash
POST /api/v1/personas/load-default-personas?set_name=set2&persona_set_name=Marketing Team Personas
```

**Result**: Creates Persona Set #2 named "Marketing Team Personas"

### Step 3: View All Sets
```bash
GET /api/v1/personas/sets
```

**Result**: Returns both sets as separate entries:
- Set #1: "Research Team Personas" (with its personas)
- Set #2: "Marketing Team Personas" (with its personas)

## Naming Conventions

### Automatic Naming

If you don't specify a custom name, the system generates names:

| File Name | Set Name Parameter | Generated Name |
|-----------|-------------------|----------------|
| `default_personas.json` | (none) | "Default Persona Set" |
| `default_personas_set1.json` | `set1` | "Set 1 Persona Set" |
| `default_personas_research.json` | `research` | "Research Persona Set" |
| `default_personas_marketing.json` | `marketing` | "Marketing Persona Set" |

### Custom Naming

You can specify custom names:
```bash
POST /api/v1/personas/load-default-personas?set_name=set1&persona_set_name=Q1 2024 Research
```

**Result**: Creates set named "Q1 2024 Research"

## Set Identification

Each set is uniquely identified by:

1. **Database ID**: Unique integer ID (e.g., `id: 1`, `id: 2`)
2. **Name**: Human-readable name (e.g., "Research Team Personas")
3. **Description**: Includes source information:
   - Which file it came from
   - Which set name was used
   - Metadata from JSON file

## Best Practices for Multiple Sets

### 1. Use Descriptive Names

```bash
# Good: Clear, descriptive names
POST /api/v1/personas/load-default-personas?set_name=research&persona_set_name=Q1 Research Personas
POST /api/v1/personas/load-default-personas?set_name=marketing&persona_set_name=Q1 Marketing Personas

# Avoid: Generic names that don't distinguish sets
POST /api/v1/personas/load-default-personas?set_name=set1&persona_set_name=Personas
POST /api/v1/personas/load-default-personas?set_name=set2&persona_set_name=Personas
```

### 2. Include Metadata in JSON Files

Add metadata to help identify sets:

```json
{
  "metadata": {
    "name": "Research Team Personas",
    "context": "Personas for Q1 2024 research project",
    "version": "1.0",
    "team": "Research",
    "project": "Q1 2024"
  },
  "personas": [...]
}
```

### 3. Organize by Purpose

Group sets logically:
- **By Project**: "Project Alpha Personas", "Project Beta Personas"
- **By Team**: "Research Team", "Marketing Team", "Product Team"
- **By Phase**: "Discovery Phase", "Validation Phase"
- **By Domain**: "Healthcare Personas", "Finance Personas"

### 4. Track Source Files

The description automatically includes source information:
- `"Loaded from set: research | File: default_personas_research.json"`

This helps you:
- Know which file a set came from
- Reload or update sets later
- Track changes over time

## Viewing Sets

### API Endpoints

1. **List All Sets**: `GET /api/v1/personas/sets`
   - Returns all sets as separate entries
   - Sorted by creation date (newest first)

2. **Get Specific Set**: `GET /api/v1/personas/sets/{persona_set_id}`
   - Returns one set with all its personas

3. **List Available Files**: `GET /api/v1/personas/available-persona-sets`
   - Shows which JSON files are available to load

### Frontend Display

- **Personas Page**: Grid/list view showing all sets
- **Each Set Shows**:
  - Set name
  - Number of personas
  - Description
  - Actions (view, expand, generate images, etc.)

## Example Workflow

```bash
# 1. Check available sets
GET /api/v1/personas/available-persona-sets
# Returns: ["default", "set1", "set2", "research"]

# 2. Load research set
POST /api/v1/personas/load-default-personas?set_name=research&persona_set_name=Research Team Q1
# Creates: Persona Set #1

# 3. Load marketing set
POST /api/v1/personas/load-default-personas?set_name=marketing&persona_set_name=Marketing Team Q1
# Creates: Persona Set #2

# 4. View all sets
GET /api/v1/personas/sets
# Returns: [
#   { "id": 1, "name": "Research Team Q1", "personas": [...] },
#   { "id": 2, "name": "Marketing Team Q1", "personas": [...] }
# ]
```

## Key Points

✅ **Each set is separate**: Different ID, name, and personas  
✅ **Fully independent**: Can be managed, analyzed, and deleted separately  
✅ **Clear identification**: Names and descriptions help distinguish sets  
✅ **Source tracking**: Description shows which file each set came from  
✅ **Easy to find**: List all sets with `GET /api/v1/personas/sets`
