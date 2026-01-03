# Custom Prompts Guide

## Where to Add Your Custom Prompts

You can customize the persona generation and expansion prompts by editing:

**File: `app/utils/prompts.py`**

This file contains three main prompts you can customize:

### 1. Persona Set Generation System Prompt

**Variable:** `PERSONA_SET_GENERATION_SYSTEM_PROMPT`

This sets the role and behavior of the AI when generating persona sets.

**Location in code:** Used in `app/core/llm_service.py` in the `generate_persona_set` method (around line 370).

**Example:**
```python
PERSONA_SET_GENERATION_SYSTEM_PROMPT = """You are an expert at creating realistic, diverse, and ethical personas based on research data and interviews."""
```

### 2. Persona Expansion System Prompt

**Variable:** `PERSONA_EXPANSION_SYSTEM_PROMPT`

This sets the role and behavior of the AI when expanding personas.

**Location in code:** Used in `app/core/llm_service.py` in the `expand_persona` method (around line 517).

**Example:**
```python
PERSONA_EXPANSION_SYSTEM_PROMPT = """You are an expert at expanding basic personas into comprehensive, detailed persona profiles based on research data and context."""
```

### 3. Persona Expansion Prompt Template

**Variable:** `PERSONA_EXPANSION_PROMPT_TEMPLATE`

This is the main prompt used for expanding personas. You can fully customize this.

**Available placeholders:**
- `{context}`: The context documents combined into a single string
- `{persona_basic}`: The basic persona data in JSON format

**Location in code:** Used in `app/core/llm_service.py` in the `expand_persona` method (around line 493).

**Example:**
```python
PERSONA_EXPANSION_PROMPT_TEMPLATE = """Expand the following basic persona into a comprehensive, detailed persona profile.

Context Information:
{context}

Basic Persona:
{persona_basic}

[Your custom instructions here...]
"""
```

## How to Customize

1. **Open** `app/utils/prompts.py`
2. **Edit** the prompt variables with your custom text
3. **Save** the file
4. **Restart** the application (Docker container) for changes to take effect

## Testing Your Changes

After modifying prompts:

1. Restart the API container:
   ```bash
   docker-compose restart api
   ```

2. Test persona generation through the frontend or API

3. Check the logs to see if prompts are being used:
   ```bash
   docker-compose logs api | grep -i "prompt\|persona"
   ```

## Notes

- The persona set generation prompt is built dynamically in `llm_service.py` based on context, interviews, and parameters. If you need to customize the main prompt structure, modify the `generate_persona_set` method in `app/core/llm_service.py` (around line 304-361).

- The expansion prompt template uses Python string formatting. Make sure to include all required placeholders (`{context}`, `{persona_basic}`) in your custom template.

- System prompts should be concise and set the AI's role/behavior. The main prompt templates contain the detailed instructions.

## Example: Custom Expansion Prompt

Here's an example of a custom expansion prompt:

```python
PERSONA_EXPANSION_PROMPT_TEMPLATE = """You are tasked with creating a detailed persona profile based on the provided context and basic persona information.

Context Information:
{context}

Basic Persona:
{persona_basic}

Please create a comprehensive persona that includes:

1. **Demographics:**
   - Age, gender, location, occupation
   - Education level, income range
   - Family status

2. **Psychographics:**
   - Values and beliefs
   - Interests and hobbies
   - Lifestyle choices

3. **Goals and Motivations:**
   - Primary goals
   - Secondary goals
   - What drives them

4. **Pain Points:**
   - Main frustrations
   - Challenges they face
   - Barriers to success

5. **Behaviors:**
   - Daily habits
   - Technology usage patterns
   - Decision-making style
   - Communication preferences

6. **Background:**
   - Personal history
   - Professional background
   - Relevant experiences

7. **Quotes:**
   - 2-3 representative quotes that capture their voice

Return the expanded persona as a JSON object with all the above fields structured clearly."""
```

