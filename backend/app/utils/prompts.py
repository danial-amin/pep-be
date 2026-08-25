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
PERSONA_SET_GENERATION_SYSTEM_PROMPT = """You are an expert at creating realistic, diverse, and ethical personas grounded in research evidence.

You prioritize consistency of place, role scope, and evidence over sounding comprehensive.
Never invent lived local concerns from distant regional statistics unless the persona's role explicitly has that wider mandate."""

# Global grounding rules — domain-agnostic; apply to every project / corpus.
# Do NOT hardcode place names, programs, or stakeholder labels here.
PERSONA_EVIDENCE_GROUNDEDNESS_RULES = """
EVIDENCE & SCOPE GROUNDING (MANDATORY — applies to every persona):

1. PLACE vs CORPUS SCOPE
   - If a persona has a stated home / work location, their background, goals, frustrations,
     motivations, behaviors, and quotes must primarily reflect that place and their daily
     situation there.
   - Source material may mention other cities, provinces, countries, or regions. Do NOT
     copy those distant places into the persona's personal goals or frustrations merely
     because they appear in the corpus.
   - Comparative or national facts may appear only when they fit the persona's role scope
     (e.g. a national analyst may reference multi-region patterns; a local resident or
     frontline local worker should not list another region's problems as their own
     lived concern). Prefer phrasing like "I've heard exclusion is worse elsewhere"
     only if interviews/context support that awareness for this role.

2. ROLE SCOPE
   - Infer each persona's operational scope from their occupation / stakeholder role:
     local, institutional-local, regional, or national.
   - Match concerns to that scope. A local household or local NGO worker stays local;
     a national-program official may use multi-region evidence, but still should not
     invent personal residence outside their stated location.

3. EVIDENCE DISCIPLINE
   - Prefer claims supported by the provided interviews/context for this persona type.
   - If a demographic attribute (e.g. gender) is not evidenced, prefer omitting it or
     using a clearly generic value rather than inventing a stereotype.
   - Do not pad goals/frustrations with impressive-sounding corpus facts that the
     persona would not personally own.

4. QUOTES & VOICE
   - Quotes must sound like this persona speaking from their place and role.
   - Do not put remote place-names into a local persona's mouth unless the source
     shows they actually discuss those places.

5. ADDITIONAL CONTEXT OVERRIDES
   - If ADDITIONAL CONTEXT, INTERVIEW TOPIC, or USER STUDY DESIGN constrain location
     or setting, treat those as hard constraints for all personas unless a persona's
     role explicitly requires a wider geographic mandate.
"""

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
#   - {stakeholder_groups_section}: Required stakeholder groups (if provided)
#   - {groundedness_section}: Global evidence/scope grounding rules
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
{additional_context_section}{interview_topic_section}{user_study_design_section}{stakeholder_groups_section}
{groundedness_section}

IMPORTANT: All personas MUST use the nested structure with a 'demographics' object. Goals and frustrations must be arrays.

OUTPUT FORMAT:
{format_instructions}
{ethical_guardrails_section}"""

# Prompt template for when only interviews are available (no context)
PERSONA_SET_GENERATION_INTERVIEWS_ONLY_TEMPLATE = """Based on the following interview data, generate {num_personas} distinct personas.

INTERVIEW DATA:
{interviews}
{additional_context_section}{interview_topic_section}{user_study_design_section}{stakeholder_groups_section}
{groundedness_section}

INSTRUCTIONS:
- Analyze the interview transcripts to identify distinct user types, needs, and behaviors
- Extract patterns, pain points, goals, and characteristics from the interviews
- Create personas that represent different user segments found in the interview data
- Base personas on actual quotes, behaviors, and needs mentioned in the interviews
- Ensure personas are diverse and represent different perspectives from the interviews
- Keep each persona's concerns consistent with their stated location and role scope

OUTPUT FORMAT:
{format_instructions}
{ethical_guardrails_section}"""

# Prompt template for when only context is available (no interviews)
PERSONA_SET_GENERATION_CONTEXT_ONLY_TEMPLATE = """Based on the following context information, generate {num_personas} distinct personas.

CONTEXT INFORMATION:
{context}
{additional_context_section}{interview_topic_section}{user_study_design_section}{stakeholder_groups_section}
{groundedness_section}

INSTRUCTIONS:
- Use the context information to understand the target market, user base, and domain
- Create personas that represent different user segments within this context
- Base personas on market research, demographics, and behavioral patterns described in the context
- Ensure personas are realistic and align with the context provided
- Consider different user needs, goals, and challenges mentioned in the context
- Keep each persona's concerns consistent with their stated location and role scope

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
PERSONA_EXPANSION_SYSTEM_PROMPT = """You are an expert at expanding basic personas into comprehensive, detailed persona profiles based on research data and context.

Preserve geographic and role-scope consistency: do not inject distant regional corpus facts into a local persona's lived goals or frustrations."""

# Main prompt template for persona expansion
# ═══════════════════════════════════════════════════════════════════════════
# YOU CAN FULLY CUSTOMIZE THIS PROMPT TO MATCH YOUR REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════
# 
# Available placeholders:
#   - {context}: The context documents combined into a single string
#   - {persona_basic}: The basic persona data in JSON format
#   - {groundedness_section}: Global evidence/scope grounding rules
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
{groundedness_section}

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. STRUCTURE REQUIREMENT:
   - ALL personas MUST use the nested structure with a 'demographics' object
   - Demographics object must contain: age, gender, location, occupation, and optionally education, nationality, income_bracket, relationship_status
   - Goals and frustrations MUST be arrays (lists), not strings
   - If the input persona has flat structure, convert it to nested structure during expansion

2. DEMOGRAPHIC FIELDS MUST REMAIN UNCHANGED:
   - DO NOT modify, expand, or change ANY demographic fields
   - Demographic fields in demographics object: age, gender, location, occupation, education, nationality, income_bracket, relationship_status
   - Keep these fields EXACTLY as they are in the original persona
   - Do NOT add details, descriptions, or explanations to demographic fields
   - If location is a string, keep it as string. If it's an object with city/country, keep that structure

3. ONLY EXPAND BEHAVIORAL AND PSYCHOGRAPHIC FIELDS:
   - ONLY expand these types of fields: behaviors, goals, motivations, frustrations, quotes, other_information, background, technology_profile
   - Add depth, detail, and richness to these fields based on the context
   - Use context information to enrich these behavioral/psychographic aspects
   - Goals and frustrations must be arrays - add more items to these arrays
   - New goals/frustrations must stay consistent with the persona's stated location and role scope

4. PRESERVE NESTED STRUCTURE:
   - Always use nested structure with demographics object
   - Do NOT add new top-level demographic fields (put them in demographics object)
   - Arrays stay as arrays, objects stay as objects
   - technology_profile should remain an object if it exists

5. EXPANSION GUIDELINES FOR BEHAVIORAL FIELDS:
   - For behavioral fields (behaviors, background): Add more detail, examples, and depth
   - For arrays (goals, frustrations, motivations): Add more items that are directly related
   - For objects (technology_profile): Expand nested fields only if they already exist
   - Use context information to add realistic, detailed behavioral insights
   - Prefer local/role-scoped evidence over distant regional statistics

6. FORMAT CONSISTENCY:
   - Maintain the exact same data types (strings stay strings, numbers stay numbers, arrays stay arrays)
   - Keep demographic fields exactly as they are (no changes)
   - Preserve any formatting conventions (e.g., if names have parentheses, keep that format)

7. WHAT NOT TO DO:
   - Do NOT modify ANY demographic fields (name, age, gender, occupation, etc.)
   - Do NOT add new demographic fields outside the demographics object
   - Do NOT add location details if location wasn't specified
   - Do NOT add employment history or background to occupation field
   - Do NOT convert arrays to strings or vice versa
   - Do NOT transplant other places' problems into this persona's personal concerns unless their role scope warrants it

Return the expanded persona as a JSON object that:
- Uses nested structure with demographics object
- Has goals and frustrations as arrays
- Keeps ALL demographic fields EXACTLY as they are (no changes)
- Only expands behavioral/psychographic fields (behaviors, goals, motivations, quotes, etc.)
- Does NOT add new fields or information"""
