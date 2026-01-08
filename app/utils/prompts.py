"""
Custom prompts for persona generation and expansion.

═══════════════════════════════════════════════════════════════════════════════
HOW TO CUSTOMIZE PROMPTS:
═══════════════════════════════════════════════════════════════════════════════

1. Edit the prompts below with your desired text
2. The prompts support Python string formatting with placeholders like {context}, {persona_basic}, etc.
3. Save the file and restart the application for changes to take effect

═══════════════════════════════════════════════════════════════════════════════
PERSONA SET GENERATION PROMPTS
═══════════════════════════════════════════════════════════════════════════════
"""

# System prompt for persona set generation
# This sets the role and behavior of the AI when generating persona sets
# You can customize this to change how the AI approaches persona generation
PERSONA_SET_GENERATION_SYSTEM_PROMPT = """You are an expert at creating realistic, diverse, and ethical personas based on research data and interviews."""

# Main prompt template for persona set generation
# ═══════════════════════════════════════════════════════════════════════════
# YOU CAN FULLY CUSTOMIZE THIS PROMPT TO MATCH YOUR REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════
# 
# Available placeholders:
#   - {num_personas}: Number of personas to generate
#   - {context}: The context documents combined into a single string
#   - {interviews}: The interview documents formatted with "Interview 1:", "Interview 2:", etc.
#   - {additional_context_section}: Additional context details (if provided)
#   - {interview_topic_section}: Interview topic information (if provided)
#   - {user_study_design_section}: User study design information (if provided)
#   - {format_instructions}: Format-specific instructions based on output_format
#   - {ethical_guardrails_section}: Ethical considerations (if enabled)
#
# Note: Sections with "_section" suffix will be empty strings if not provided,
# so they won't add extra blank lines in the final prompt.
#
# Prompt template for when both interviews and context are available
PERSONA_SET_GENERATION_PROMPT_TEMPLATE = """Based on the following context and interview data, generate {num_personas} distinct personas.

CONTEXT INFORMATION:
{context}

INTERVIEW DATA:
{interviews}
{additional_context_section}{interview_topic_section}{user_study_design_section}
OUTPUT FORMAT:
{format_instructions}
{ethical_guardrails_section}"""

# Prompt template for when only interviews are available (no context)
PERSONA_SET_GENERATION_INTERVIEWS_ONLY_TEMPLATE = """Based on the following interview data, generate {num_personas} distinct personas.

INTERVIEW DATA:
{interviews}
{additional_context_section}{interview_topic_section}{user_study_design_section}

INSTRUCTIONS:
- Analyze the interview transcripts to identify distinct user types, needs, and behaviors
- Extract patterns, pain points, goals, and characteristics from the interviews
- Create personas that represent different user segments found in the interview data
- Base personas on actual quotes, behaviors, and needs mentioned in the interviews
- Ensure personas are diverse and represent different perspectives from the interviews

OUTPUT FORMAT:
{format_instructions}
{ethical_guardrails_section}"""

# Prompt template for when only context is available (no interviews)
PERSONA_SET_GENERATION_CONTEXT_ONLY_TEMPLATE = """Based on the following context information, generate {num_personas} distinct personas.

CONTEXT INFORMATION:
{context}
{additional_context_section}{interview_topic_section}{user_study_design_section}

INSTRUCTIONS:
- Use the context information to understand the target market, user base, and domain
- Create personas that represent different user segments within this context
- Base personas on market research, demographics, and behavioral patterns described in the context
- Ensure personas are realistic and align with the context provided
- Consider different user needs, goals, and challenges mentioned in the context

OUTPUT FORMAT:
{format_instructions}
{ethical_guardrails_section}"""


"""
═══════════════════════════════════════════════════════════════════════════════
PERSONA EXPANSION PROMPTS
═══════════════════════════════════════════════════════════════════════════════
"""

# System prompt for persona expansion
# This sets the role and behavior of the AI when expanding personas
# You can customize this to change how the AI approaches persona expansion
PERSONA_EXPANSION_SYSTEM_PROMPT = """You are an expert at expanding basic personas into comprehensive, detailed persona profiles based on research data and context."""

# Main prompt template for persona expansion
# ═══════════════════════════════════════════════════════════════════════════
# YOU CAN FULLY CUSTOMIZE THIS PROMPT TO MATCH YOUR REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════
# 
# Available placeholders:
#   - {context}: The context documents combined into a single string
#   - {persona_basic}: The basic persona data in JSON format
#
# Example usage:
#   - Add your own instructions
#   - Modify the structure
#   - Add specific fields you want
#   - Change the output format requirements
#
PERSONA_EXPANSION_PROMPT_TEMPLATE = """Expand the following basic persona into a comprehensive, detailed persona profile.

Context Information:
{context}

Basic Persona:
{persona_basic}

Create a detailed persona profile that includes:
- Name and demographics (age, gender, location, occupation)
- Background and personal history
- Goals and motivations
- Pain points and frustrations
- Behaviors and preferences
- Technology usage and digital literacy
- Quotes or key statements that represent this persona
- Detailed description of their needs and how they interact with the product/service

Ensure the expanded persona is:
- Realistic and based on the provided context
- Detailed and specific (not generic)
- Coherent with the basic persona characteristics
- Rich in detail that can inform product design decisions

Return the expanded persona as a JSON object with all the above fields."""
