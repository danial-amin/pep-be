# Frontend to Prompts Flow - Complete ✅

## Overview

All the values needed for persona generation come from the frontend and flow through to the customizable prompts. Here's the complete flow:

## Data Flow

```
Frontend (PersonasPage.tsx)
    ↓
API Service (api.ts)
    ↓
API Endpoint (personas.py)
    ↓
Persona Service (persona_service.py)
    ↓
LLM Service (llm_service.py)
    ↓
Custom Prompts (prompts.py)
```

## Frontend Input Fields

**File:** `frontend/src/pages/PersonasPage.tsx`

### Basic Options (Always Visible)
- **Number of Personas** (`numPersonas`) - Number input
- **Output Format** (`outputFormat`) - Dropdown: json, profile, chat, proto, adhoc, engaging, goal_based, role_based, interactive

### Advanced Options (Collapsible)
- **Context Details** (`contextDetails`) - Textarea for additional context about research/market/domain
- **Interview Topic** (`interviewTopic`) - Text input for what interviews are about
- **User Study Design** (`userStudyDesign`) - Textarea for methodology and research approach
- **Include Ethical Guardrails** (`includeEthicalGuardrails`) - Checkbox (default: true)

## API Request

**File:** `frontend/src/services/api.ts`

```typescript
personasApi.generateSet(
  numPersonas,
  contextDetails || undefined,
  interviewTopic || undefined,
  userStudyDesign || undefined,
  includeEthicalGuardrails,
  outputFormat
)
```

**Sends to:** `POST /api/v1/personas/generate-set`

**Request Body:**
```json
{
  "num_personas": 3,
  "context_details": "...",
  "interview_topic": "...",
  "user_study_design": "...",
  "include_ethical_guardrails": true,
  "output_format": "json"
}
```

## Backend Processing

### 1. API Endpoint
**File:** `app/api/v1/endpoints/personas.py`

Receives `PersonaSetCreateRequest` with all fields and passes them to the service.

### 2. Persona Service
**File:** `app/services/persona_service.py`

Receives all parameters and passes them to LLM service:
```python
persona_set_data = await llm_service.generate_persona_set(
    interview_documents=interview_texts,
    context_documents=context_texts,
    num_personas=num_personas,
    context_details=context_details,  # ← From frontend
    interview_topic=interview_topic,   # ← From frontend
    user_study_design=user_study_design,  # ← From frontend
    include_ethical_guardrails=include_ethical_guardrails,  # ← From frontend
    output_format=output_format  # ← From frontend
)
```

### 3. LLM Service
**File:** `app/core/llm_service.py`

Builds sections from frontend values and uses them in the customizable prompt template:

```python
# Build sections from frontend values
additional_context_section = ""
if context_details:  # ← From frontend
    additional_context_section = f"\n\nADDITIONAL CONTEXT:\n{context_details}"

interview_topic_section = ""
if interview_topic:  # ← From frontend
    interview_topic_section = f"\n\nINTERVIEW TOPIC:\nThe interviews focus on: {interview_topic}"

user_study_design_section = ""
if user_study_design:  # ← From frontend
    user_study_design_section = f"\n\nUSER STUDY DESIGN:\n{user_study_design}"

ethical_guardrails_section = ""
if include_ethical_guardrails:  # ← From frontend
    ethical_guardrails_section = """\n\nETHICAL AND FAIRNESS CONSIDERATIONS:..."""

# Use customizable prompt template
prompt = PERSONA_SET_GENERATION_PROMPT_TEMPLATE.format(
    num_personas=num_personas,  # ← From frontend
    context=context,
    interviews=interviews,
    additional_context_section=additional_context_section,  # ← From frontend
    interview_topic_section=interview_topic_section,  # ← From frontend
    user_study_design_section=user_study_design_section,  # ← From frontend
    format_instructions=format_instructions,  # ← Based on output_format from frontend
    ethical_guardrails_section=ethical_guardrails_section  # ← From frontend
)
```

### 4. Custom Prompts
**File:** `app/utils/prompts.py`

The template receives all values from frontend:

```python
PERSONA_SET_GENERATION_PROMPT_TEMPLATE = """Based on the following context and interview data, generate {num_personas} distinct personas.

CONTEXT INFORMATION:
{context}

INTERVIEW DATA:
{interviews}
{additional_context_section}{interview_topic_section}{user_study_design_section}
OUTPUT FORMAT:
{format_instructions}
{ethical_guardrails_section}"""
```

## Summary

✅ **All values come from the frontend**
✅ **Flow is complete: Frontend → API → Service → LLM → Prompts**
✅ **All fields are optional (except num_personas)**
✅ **Values are properly passed through all layers**
✅ **Custom prompts receive all frontend values**

## Customization

You can customize how these frontend values are used in the prompts by editing:
- `app/utils/prompts.py` - Modify the prompt template structure
- The template will automatically receive all values from the frontend

## Testing

1. Open the frontend Personas page
2. Fill in the advanced options (Context Details, Interview Topic, User Study Design)
3. Select output format and ethical guardrails option
4. Generate personas
5. Check API logs to see the values being used in prompts

