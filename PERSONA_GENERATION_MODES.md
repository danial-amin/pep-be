# Persona Generation Modes

## Overview

The persona generation system now supports three different modes based on what documents are available:

1. **Interviews Only**: Generate personas from interview transcripts
2. **Context Only**: Generate personas from context/research documents
3. **Both**: Generate personas using both interviews and context (recommended)

Each mode uses a different prompt template optimized for the available data.

## Mode 1: Interviews Only

### When to Use
- You have interview transcripts but no context documents
- You want personas based directly on user interviews
- You're working with qualitative interview data

### How It Works
1. System retrieves relevant chunks from interview documents
2. Uses `PERSONA_SET_GENERATION_INTERVIEWS_ONLY_TEMPLATE` prompt
3. Focuses on extracting patterns, needs, and behaviors from interviews
4. Creates personas based on actual quotes and behaviors mentioned

### Prompt Characteristics
- Emphasizes analyzing interview transcripts
- Extracts distinct user types from interview data
- Bases personas on actual quotes and needs from interviews
- Focuses on patterns found in the interview data

### Example
```python
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "document_ids": [1, 2, 3]  # Only interview documents
}
```

## Mode 2: Context Only

### When to Use
- You have market research, demographics, or context documents
- You don't have interview transcripts yet
- You want to create proto-personas based on research
- You're working with quantitative or secondary research data

### How It Works
1. System retrieves relevant chunks from context documents
2. Uses `PERSONA_SET_GENERATION_CONTEXT_ONLY_TEMPLATE` prompt
3. Focuses on market research, demographics, and behavioral patterns
4. Creates personas aligned with the context provided

### Prompt Characteristics
- Emphasizes using context information to understand target market
- Creates personas representing different user segments
- Bases personas on market research and demographics
- Considers user needs, goals, and challenges from context

### Example
```python
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "document_ids": [4, 5]  # Only context documents
}
```

## Mode 3: Both Interviews and Context (Recommended)

### When to Use
- You have both interview transcripts and context documents
- You want the most comprehensive and accurate personas
- You're doing full user research with multiple data sources
- This is the recommended approach for best results

### How It Works
1. System retrieves relevant chunks from both interview and context documents
2. Uses `PERSONA_SET_GENERATION_PROMPT_TEMPLATE` (standard template)
3. Combines insights from interviews with market context
4. Creates personas that are both data-driven (interviews) and contextually informed

### Prompt Characteristics
- Combines interview insights with market context
- Uses interviews for specific user needs and behaviors
- Uses context for market understanding and demographics
- Creates well-rounded personas with both qualitative and quantitative backing

### Example
```python
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "document_ids": [1, 2, 3, 4, 5]  # Both interview and context documents
}
```

## Automatic Mode Detection

The system automatically detects which mode to use based on available documents:

```python
# In persona_service.py
has_interviews = len(interview_texts) > 0
has_context = len(context_texts) > 0

# Automatically selects appropriate prompt template
if has_interviews and has_context:
    # Use standard template (both)
elif has_interviews and not has_context:
    # Use interviews-only template
elif has_context and not has_interviews:
    # Use context-only template
else:
    # Error: no documents available
```

## Validation

The system validates that at least one type of document is available:

```python
if not interviews and not contexts:
    raise ValueError(
        "No documents found. Please process at least one interview "
        "or context document first."
    )
```

## Customizing Prompts

You can customize the prompts for each mode in `app/utils/prompts.py`:

- `PERSONA_SET_GENERATION_PROMPT_TEMPLATE` - Both interviews and context
- `PERSONA_SET_GENERATION_INTERVIEWS_ONLY_TEMPLATE` - Interviews only
- `PERSONA_SET_GENERATION_CONTEXT_ONLY_TEMPLATE` - Context only

Each template supports the same placeholders:
- `{num_personas}` - Number of personas to generate
- `{context}` - Context documents (empty if not available)
- `{interviews}` - Interview documents (empty if not available)
- `{additional_context_section}` - Additional context details
- `{interview_topic_section}` - Interview topic information
- `{user_study_design_section}` - User study design
- `{format_instructions}` - Format-specific instructions
- `{ethical_guardrails_section}` - Ethical considerations

## Best Practices

1. **Use Both When Possible**: Combining interviews and context gives the best results
2. **Interviews for Specificity**: Interviews provide real user quotes and behaviors
3. **Context for Market Understanding**: Context provides demographic and market insights
4. **Project Isolation**: Use `project_id` or `document_ids` to ensure session isolation
5. **Quality Over Quantity**: Better to have fewer high-quality documents than many low-quality ones

## Example Workflows

### Workflow 1: Start with Context, Add Interviews Later
```python
# Step 1: Upload context documents
POST /api/v1/documents/process
{
    "file": market_research.pdf,
    "document_type": "context",
    "project_id": "project-1"
}

# Step 2: Generate initial personas from context
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "project_id": "project-1"
}

# Step 3: Later, add interviews
POST /api/v1/documents/process
{
    "file": interviews.pdf,
    "document_type": "interview",
    "project_id": "project-1"
}

# Step 4: Regenerate with both (better personas)
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "project_id": "project-1"
}
```

### Workflow 2: Interviews First
```python
# Step 1: Upload interviews
POST /api/v1/documents/process
{
    "file": user_interviews.pdf,
    "document_type": "interview",
    "project_id": "project-2"
}

# Step 2: Generate personas from interviews
POST /api/v1/personas/generate-set
{
    "num_personas": 3,
    "project_id": "project-2"
}
```

## Technical Notes

- The system uses RAG (Retrieval Augmented Generation) to retrieve relevant chunks
- Vector database filtering ensures only relevant documents are used
- Token limits are handled automatically with summarization
- All three modes support the same advanced options (format, ethical guardrails, etc.)
