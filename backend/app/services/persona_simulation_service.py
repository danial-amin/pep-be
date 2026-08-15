"""
Persona Simulation Service - orchestrates multi-persona LLM conversations.

This service enables multiple persona-infused LLMs to conduct structured
simulations of discussion, with each agent grounded in behavioral data via RAG.

Key design principles (all production defaults):
  1. BLIND OPENING: each agent writes their opening statement without seeing
     what other agents said first, producing genuinely independent starting
     positions rather than convergence from turn 1.
  2. GROUP MANDATES: when agents carry a role (e.g. "teacher" / "student"),
     a group-specific mandate is injected into their system prompt, encoding
     the structural tension between groups.
  3. NON-NEGOTIABLES: the agent's primary frustration becomes an explicit
     position they cannot abandon without a documented reason, preventing
     costless capitulation.
  4. STANCE ACCOUNTABILITY: agents must say explicitly when and why their
     position changes; agreement without stated reason is disallowed.
  5. FINAL POSITION DECLARATION: the last round forces each agent to state
     their final position and account for any change from their opening.
  6. PHASED MID-TURNS: after openings, prompts move challenge → propose → decide
     with a rotating rhetorical move per speaker/round, and ban agree-first
     restatement so agents advance stakes instead of circling politely.
  7. TOKEN BUDGET: SIMULATION_MAX_OUTPUT_TOKENS per turn (default 400), clamped 200–800 in code.
  8. NO PERIODIC REMINDER: CORE IDENTITY ANCHOR in the system prompt does
     the stability work; a mid-conversation reminder is a confound.
"""
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime, timezone
import json
import logging
import asyncio
import re

from app.core.config import settings
from app.core.openai_compat import chat_completion_kwargs
from app.core.vector_db import vector_db
from app.models.simulation import Simulation, SimulationParticipant, SimulationMessage
from app.utils.rag_filter import get_project_document_filter
from app.models.persona import Persona
from app.utils.token_utils import estimate_tokens

logger = logging.getLogger(__name__)

# ─── Token budget ──────────────────────────────────────────────────────────────
# Output cap per turn: settings.SIMULATION_MAX_OUTPUT_TOKENS (default 400).
# Count only completion tokens toward simulation.tokens_used (not full prompt+completion).

_SIMULATION_REPLY_LENGTH = (
    "LENGTH: Keep answers short and to the point — usually 2–4 sentences. "
    "One clear claim, brief reason, then stop. No preamble, no lists, no restating the whole debate. "
    "Always finish with a complete sentence — never stop mid-thought."
)

# Prefer variety over a hard ban: the agree→gloss template is fine sometimes,
# especially early, but must not be the only shape.
_STYLE_VARIETY = (
    "STYLE: Do not use the same reply shape every turn. "
    "Especially after the opening, mix how you enter — challenge, personal stake, "
    "hard question, counterexample, priority, or a blunt line. "
    "Brief genuine agreement is fine when earned, but do not open every turn with "
    "'I agree' / 'You're right' / 'That makes sense' / 'Fair point' and then a soft gloss. "
    "If you agree, immediately add a new stake, constraint, or concrete next step."
)

# Rotating rhetorical moves so mid-discussion does not converge on one voice.
_RHETORICAL_MOVES = (
    (
        "pushback",
        "Open with a clear disagreement, caveat, or risk others are underplaying.",
    ),
    (
        "personal_stake",
        "Lead with one concrete detail from your own life or work that others have not used yet. "
        "Then tie it to what you want changed.",
    ),
    (
        "hard_question",
        "Ask one pointed tradeoff question that forces a real choice. "
        "Then state which side you take and why.",
    ),
    (
        "counterexample",
        "Give a concrete case or edge case that complicates the last claim. "
        "Do not politely summarize that claim first.",
    ),
    (
        "priority",
        "Name your top priority and what you would deprioritize. "
        "Make the ranking explicit; do not circle back to vague common ground.",
    ),
    (
        "blunt_line",
        "State one thing you will not accept. Keep it short and specific. "
        "Only then, if needed, offer one condition under which you might move.",
    ),
    (
        "earned_agree",
        "If — and only if — someone made a point that genuinely addresses your concern, "
        "acknowledge it in one short clause, then advance with a new requirement or next step. "
        "Do not use empty politeness agreement.",
    ),
)

# ─── Group mandates ────────────────────────────────────────────────────────────
# Injected into the system prompt when a participant carries a known role.
# Mandates encode the structural tension between groups — they are partially
# compatible but not fully reconcilable, which is what forces genuine exchange.
# Extend this dict as new role types are added.
_GROUP_MANDATES: Dict[str, str] = {
    "teacher": (
        "YOUR GROUP MANDATE (Teachers):\n"
        "Cipherbot must protect the integrity of the learning process. It must stay "
        "within the uploaded course material, must not do the student's thinking for "
        "them, and must never provide a direct answer to an assessment question. "
        "Your job is to ensure students learn, not just get answers."
    ),
    "student": (
        "YOUR GROUP MANDATE (Students):\n"
        "Cipherbot must give you direct, accessible help when you need it. It must "
        "respond in plain language without requiring prior subject knowledge to "
        "understand the answer, and it must not make you feel stupid for asking a "
        "question. Your job is to get the help you need to succeed."
    ),
}


class PersonaSimulationService:
    """Service for running multi-persona simulations of discussion."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @staticmethod
    def _max_output_tokens() -> int:
        """Per persona message: enough headroom to finish complete sentences."""
        n = getattr(settings, "SIMULATION_MAX_OUTPUT_TOKENS", 400)
        return max(200, min(int(n), 800))

    # ──────────────────────────────────────────────────────────────────────────
    # Prompt building
    # ──────────────────────────────────────────────────────────────────────────

    def _build_persona_system_prompt(
        self,
        persona: Persona,
        role: Optional[str] = None,
        facilitator_must_address: Optional[str] = None,
    ) -> str:
        """
        Build the system prompt for one agent turn.

        Includes:
          - Full persona profile (background, goals, frustrations, behaviours)
          - CORE IDENTITY ANCHOR (primary traits that must never be abandoned)
          - NON-NEGOTIABLE derived from the agent's strongest frustration
          - Group mandate when a known role is provided
          - Stance accountability instruction
        """
        persona_data = persona.persona_data or {}

        name       = persona_data.get("name", persona.name)
        demographics = persona_data.get("demographics", {})
        background   = persona_data.get("background", "")
        goals        = persona_data.get("goals", [])
        frustrations = persona_data.get("frustrations", [])
        motivations  = persona_data.get("motivations", [])
        behaviors    = persona_data.get("behaviors", "")
        quote        = persona_data.get("quote", "")
        starting_position = (persona_data.get("starting_position") or "").strip()
        tech = persona_data.get("technology_profile")
        interaction_prefs = []
        if isinstance(tech, dict):
            prefs = tech.get("interaction_preferences")
            if isinstance(prefs, list):
                interaction_prefs = [str(p) for p in prefs if p][:4]

        # ── Demographic string ──────────────────────────────────────────────
        demo_parts = []
        if demographics.get("age"):
            demo_parts.append(f"{demographics['age']} years old")
        if demographics.get("gender"):
            demo_parts.append(demographics["gender"])
        if demographics.get("occupation"):
            demo_parts.append(f"works as {demographics['occupation']}")
        if demographics.get("location"):
            loc = demographics["location"]
            if isinstance(loc, dict):
                loc = f"{loc.get('city', '')}, {loc.get('country', '')}".strip(", ")
            demo_parts.append(f"from {loc}")
        demographic_str = ", ".join(demo_parts) if demo_parts else "a professional"

        # ── Formatted lists ─────────────────────────────────────────────────
        goals_str        = "\n".join([f"  - {g}" for g in goals])        if goals        else "  - Not specified"
        frustrations_str = "\n".join([f"  - {f}" for f in frustrations]) if frustrations else "  - Not specified"
        motivations_str  = "\n".join([f"  - {m}" for m in motivations])  if motivations  else ""
        prefs_str        = "\n".join([f"  - {p}" for p in interaction_prefs]) if interaction_prefs else ""

        # ── Core identity anchor ─────────────────────────────────────────────
        primary_goal        = goals[0]        if goals        else "personal growth"
        primary_frustration = frustrations[0] if frustrations else "lack of progress"
        primary_motivation  = motivations[0]  if motivations  else "making a difference"
        core_behavior       = behaviors.split(".")[0].strip() if behaviors else "thoughtful and deliberate"

        core_identity_section = f"""
CORE IDENTITY ANCHOR — NEVER ABANDON THESE:
  • Primary drive:             {primary_goal}
  • Key frustration:           {primary_frustration}
  • Core motivation:           {primary_motivation}
  • Characteristic behaviour:  {core_behavior}
  • Your authentic voice:      "{quote}"

These define WHO YOU ARE. You may revise individual opinions if another participant
gives you a genuine reason to do so, but your personality, values, and communication
style must remain consistent in every single message you produce."""

        # ── Non-negotiable ───────────────────────────────────────────────────
        # Derived from the agent's strongest frustration. This is the one
        # position they cannot drop without explicitly stating what changed
        # their mind. It prevents costless capitulation in later turns.
        non_negotiable_section = ""
        if frustrations:
            non_negotiable_section = f"""
NON-NEGOTIABLE POSITION:
The following concern is central to your stakeholder perspective. You will not
abandon it unless another participant directly addresses it with a specific,
reasoned argument. If you change this position, you must name the argument
that convinced you.
  "{frustrations[0]}"
"""

        # ── Group mandate ─────────────────────────────────────────────────────
        group_mandate_section = ""
        if role and role.lower() in _GROUP_MANDATES:
            group_mandate_section = f"\n{_GROUP_MANDATES[role.lower()]}\n"

        # ── Stance accountability ─────────────────────────────────────────────
        stance_instruction = """
STANCE ACCOUNTABILITY:
You may change your position during this discussion, but only if another
participant has offered a specific reason that genuinely addresses your concern.
When you change your position, say so explicitly: name the argument that
persuaded you. Do not agree with others simply to be agreeable or to move the
conversation forward. Surface agreement without genuine persuasion is not
acceptable."""

        starting_position_section = ""
        if starting_position:
            starting_position_section = f"""
YOUR STARTING POSITION ON THIS KIND OF ISSUE:
{starting_position}
Hold this unless someone gives you a specific reason to revise it.
"""

        voice_section = ""
        if prefs_str:
            voice_section = f"""
HOW YOU TEND TO COMMUNICATE:
{prefs_str}
Let these shape your wording and rhythm — do not sound like a generic meeting participant.
"""

        # ── Assemble ─────────────────────────────────────────────────────────
        system_prompt = f"""You are {name}, {demographic_str}.

BACKGROUND:
{background}

YOUR GOALS:
{goals_str}

YOUR FRUSTRATIONS AND PAIN POINTS:
{frustrations_str}

{"YOUR MOTIVATIONS:" if motivations_str else ""}
{motivations_str}

{"BEHAVIOURAL TRAITS:" if behaviors else ""}
{behaviors}
{starting_position_section}
{voice_section}
{core_identity_section}
{non_negotiable_section}
{group_mandate_section}
{stance_instruction}

CONVERSATION GUIDELINES:
- Respond authentically as this persona, drawing from your background, goals, and frustrations
- Share one focused perspective per turn — one concrete detail beats a long essay
- Do NOT spend the turn summarizing or paraphrasing what others just said
- Advance the discussion: add a new stake, constraint, example, risk, or concrete option
- Challenge a real tension when you disagree; do not politely restate common ground
- Naming another participant is optional — only do it when you challenge or build on a specific claim of theirs
- If you have expertise relevant to the topic, mention it briefly
- Express frustrations when relevant, in one tight sentence if possible
- NEVER adopt another participant's communication style — remain distinctly yourself
- Mix your reply shape across turns; do not settle into one fixed template
- {_STYLE_VARIETY}
- {_SIMULATION_REPLY_LENGTH}"""

        if facilitator_must_address:
            system_prompt += f"""

CRITICAL — FACILITATOR INTERVENTION:
The facilitator has said: "{facilitator_must_address}"
Address this directly in your next response. Let it change the course of your
reply. Do not continue the previous thread without engaging the intervention.
Bring your own stake — do not only agree or politely acknowledge.
{_STYLE_VARIETY}
{_SIMULATION_REPLY_LENGTH}"""

        return system_prompt

    # ──────────────────────────────────────────────────────────────────────────
    # Group mandate helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_role(participant_roles: Dict[int, Optional[str]], persona_id: int) -> Optional[str]:
        return participant_roles.get(persona_id)

    # ──────────────────────────────────────────────────────────────────────────
    # Turn prompt selection
    # ──────────────────────────────────────────────────────────────────────────

    def _discussion_phase(self, completed_before: int, max_turns: int) -> str:
        """Map progress through the run to a phase that reduces circular mid-talk."""
        # Opening turns use the blind prompt; final round uses the closing prompt.
        # Phases apply only to middle continues.
        usable = max(1, max_turns - 1)  # rounds before the designated final round
        progress = completed_before / usable
        if progress < 0.34:
            return "challenge"
        if progress < 0.67:
            return "propose"
        return "decide"

    @staticmethod
    def _rhetorical_move(persona_id: int, completed_before: int) -> tuple:
        """Pick a reply shape that varies by speaker and round — avoids one shared template."""
        idx = (int(persona_id or 0) + int(completed_before or 0) * 3) % len(_RHETORICAL_MOVES)
        return _RHETORICAL_MOVES[idx]

    def _build_turn_prompt(
        self,
        simulation: Simulation,
        is_first_turn_for_agent: bool,
        is_last_facilitator: bool,
        last_facilitator_content: Optional[str],
        other_participant_names: List[str],
        is_final_round: bool,
        completed_before: int = 0,
        persona_id: Optional[int] = None,
    ) -> str:
        """
        Return the user-turn prompt appropriate for the current moment.

          Opening (agent's first turn): stance declaration — agent commits to
            a specific position before seeing what others said.
          Final round: closing declaration — agent states final position and
            accounts for any change.
          Facilitator intervention: acknowledgement required.
          Mid turns: phase prompts (challenge → propose → decide) plus a
            rotating rhetorical move so agents do not circle in one style.
        """
        goal_context_block = ""
        if simulation.goal_context and str(simulation.goal_context).strip():
            goal_context_block = str(simulation.goal_context).strip() + "\n\n"

        # ── Opening turn (blind) ──────────────────────────────────────────────
        if is_first_turn_for_agent:
            # Must follow simulation.goal only — never inject unrelated product/study
            # names (e.g. a fixed chatbot scenario) or the personas will hallucinate them.
            # First turns may use a natural stance style; variety is enforced on later turns.
            return f"""The topic for this discussion is: {simulation.goal}

{goal_context_block}State your position clearly on this topic: what do you advocate for, and what do you oppose or resist?
Name one stance you support and one you oppose, each with one short reason.
{_SIMULATION_REPLY_LENGTH}"""

        # ── Final round ───────────────────────────────────────────────────────
        if is_final_round:
            return f"""This is the final round of the discussion. State your final position on the topic: {simulation.goal}

If your view has changed from what you said at the start, name specifically
which argument changed your mind. If your view has not changed, say so and
explain why the discussion did not shift your position.
End with one concrete priority or next step you would insist on.
Do not only recap the conversation — land on your final stake.
{_SIMULATION_REPLY_LENGTH}"""

        # ── Facilitator intervention ──────────────────────────────────────────
        if is_last_facilitator and last_facilitator_content:
            return f"""The facilitator has just said: "{last_facilitator_content}"

Respond directly to this. Let it change the direction of your reply.
Bring in your own stake — do not only acknowledge the facilitator.
{_STYLE_VARIETY}
{_SIMULATION_REPLY_LENGTH}"""

        # ── Standard continue turn (phased + rhetorical move) ─────────────────
        facilitator_note = ""
        if last_facilitator_content:
            facilitator_note = f'The facilitator recently said: "{last_facilitator_content}" — keep this in mind.\n\n'

        phase = self._discussion_phase(completed_before, simulation.max_turns or 10)
        move_name, move_instruction = self._rhetorical_move(
            persona_id or 0, completed_before
        )
        # Prefer non-agree shapes for most mid-turns; "earned_agree" is only ~1/7 of the rotation.
        names_hint = (
            f"Other participants: {', '.join(other_participant_names)}."
            if other_participant_names
            else ""
        )

        anti_circle = (
            "Do not summarize or politely rephrase what was just said. "
            "Add something new from your perspective. "
            "Do not end by circling back to a vague shared hope."
        )

        if phase == "challenge":
            phase_instruction = (
                "Push on a real tension. Name a conflict, risk, or non-negotiable "
                "that others have not fully faced yet."
            )
        elif phase == "propose":
            phase_instruction = (
                "Propose one concrete option, tradeoff, or design/policy choice. "
                "Say what you would accept and what you would refuse."
            )
        else:
            phase_instruction = (
                "Move toward a decision. State your top priority and one thing "
                "you will not concede. If helpful, name who you need to convince."
            )

        return f"""{facilitator_note}Continue the discussion on: {simulation.goal}
{names_hint}
{anti_circle}
{phase_instruction}
THIS TURN'S REPLY SHAPE ({move_name}): {move_instruction}
Use this shape for this turn — do not fall back to the same agree-then-comment pattern every time.
{_STYLE_VARIETY}
If you change your earlier view, say so explicitly and name what persuaded you.
{_SIMULATION_REPLY_LENGTH}"""

    # ──────────────────────────────────────────────────────────────────────────
    # RAG grounding
    # ──────────────────────────────────────────────────────────────────────────

    async def _get_rag_grounding(
        self,
        session: AsyncSession,
        simulation: Simulation,
        messages_ordered: List[SimulationMessage],
        participants: Dict[int, Persona],
    ) -> str:
        """Retrieve relevant document chunks to ground persona responses."""
        query_parts = [simulation.goal]
        if simulation.goal_context:
            query_parts.append(simulation.goal_context)
        persona_msgs = [
            m for m in messages_ordered
            if not (getattr(m, "is_human_message", False) or m.persona_id is None)
        ]
        for m in persona_msgs[-3:]:
            p = participants.get(m.persona_id)
            name = p.name if p else "Unknown"
            query_parts.append(f"{name}: {m.content}")
        query_text = " ".join(query_parts).strip() or simulation.goal
        if not query_text:
            return ""

        filter_metadata = None
        project_id = getattr(simulation, "project_id", None)
        if project_id is not None:
            filter_metadata = await get_project_document_filter(
                session, project_id, "interview"
            )

        try:
            result = await vector_db.query_documents(
                query_texts=[query_text],
                n_results=10,
                filter_metadata=filter_metadata,
            )
            docs = result.get("documents")
            if not docs or not docs[0]:
                return ""
            chunks = docs[0]
            seen, unique, total = set(), [], 0
            for c in chunks:
                if c and c not in seen and total + len(c) <= 6000:
                    seen.add(c)
                    unique.append(c)
                    total += len(c)
            return "\n\n---\n\n".join(unique) if unique else ""
        except Exception as e:
            logger.warning(f"RAG grounding failed for simulation {simulation.id}: {e}", exc_info=True)
            return ""

    # ──────────────────────────────────────────────────────────────────────────
    # Facilitator context
    # ──────────────────────────────────────────────────────────────────────────

    def _get_facilitator_context(
        self, messages: List[SimulationMessage]
    ) -> tuple[Optional[str], bool]:
        """Returns (last_facilitator_content, is_last_message_facilitator)."""
        msgs = self._chronological_messages(messages)
        if not msgs:
            return None, False
        last_facilitator_content = None
        for m in msgs:
            if getattr(m, "is_human_message", False) or m.persona_id is None:
                last_facilitator_content = m.content
        last = msgs[-1]
        is_last_facilitator = (
            getattr(last, "is_human_message", False) or last.persona_id is None
        )
        return last_facilitator_content, is_last_facilitator

    # ──────────────────────────────────────────────────────────────────────────
    # Conversation context
    # ──────────────────────────────────────────────────────────────────────────

    def _build_conversation_context(
        self,
        messages: List[SimulationMessage],
        participants: Dict[int, Persona],
        current_persona_id: int,
    ) -> List[Dict[str, str]]:
        """
        Build the conversation history for the LLM context.

        BLIND OPENING: if this agent has not yet spoken, return an empty
        context. Each agent writes their opening statement without seeing
        what others said first. This produces genuinely independent starting
        positions rather than immediate convergence toward the first speaker.
        """
        agent_has_spoken = any(
            m.persona_id == current_persona_id
            for m in messages
            if not getattr(m, "is_human_message", False) and m.persona_id is not None
        )
        if not agent_has_spoken:
            return []

        context = []
        for msg in messages:
            is_human = getattr(msg, "is_human_message", False) or msg.persona_id is None
            if is_human:
                context.append({
                    "role": "user",
                    "content": f"[Facilitator]: {msg.content}"
                })
                continue
            persona = participants.get(msg.persona_id)
            persona_name = persona.name if persona else "Unknown"
            if msg.persona_id == current_persona_id:
                context.append({"role": "assistant", "content": msg.content})
            else:
                context.append({"role": "user", "content": f"[{persona_name}]: {msg.content}"})
        return context

    # ──────────────────────────────────────────────────────────────────────────
    # Core turn generation
    # ──────────────────────────────────────────────────────────────────────────

    async def generate_turn(
        self,
        simulation: Simulation,
        session: AsyncSession,
    ) -> Optional[SimulationMessage]:
        """Generate the next turn in the simulation."""
        if simulation.status in ("completed", "stopped"):
            return None

        # ── Load participants ─────────────────────────────────────────────────
        participants: Dict[int, Persona] = {}
        participant_roles: Dict[int, Optional[str]] = {}
        for p in simulation.participants:
            result = await session.execute(select(Persona).where(Persona.id == p.persona_id))
            persona = result.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona
                participant_roles[p.persona_id] = p.role

        if not participants:
            logger.error(f"No valid participants for simulation {simulation.id}")
            return None

        # Speaking order = participant creation order (study Latin-square when created that way)
        participant_ids = [
            p.persona_id
            for p in sorted(simulation.participants, key=lambda sp: sp.id or 0)
            if p.persona_id in participants
        ] or list(participants.keys())

        num_participants = len(participant_ids)
        persona_count_before = self._count_persona_messages(list(simulation.messages))
        completed_before = self._completed_full_rounds(persona_count_before, num_participants)
        # max_turns = number of full rounds (schema). Stop only after that many rounds finish.
        if completed_before >= simulation.max_turns:
            simulation.status = "completed"
            simulation.completed_at = datetime.now(timezone.utc)
            simulation.current_turn = completed_before
            await session.commit()
            return None

        messages_ordered = self._chronological_messages(list(simulation.messages))
        next_speaker_id = self._select_next_speaker(
            messages_ordered,
            participant_ids,
            simulation.current_turn,
            participants=participants,
        )
        next_persona = participants[next_speaker_id]
        next_role = participant_roles.get(next_speaker_id)

        last_facilitator_content, is_last_facilitator = self._get_facilitator_context(
            messages_ordered
        )
        facilitator_must_address = last_facilitator_content if is_last_facilitator else None

        # ── System prompt ─────────────────────────────────────────────────────
        system_prompt = self._build_persona_system_prompt(
            next_persona,
            next_role,
            facilitator_must_address=facilitator_must_address,
        )

        rag_grounding = await self._get_rag_grounding(
            session, simulation, messages_ordered, participants
        )
        if rag_grounding:
            system_prompt += (
                "\n\nGROUNDING — EVIDENCE FROM PROJECT DOCUMENTS (use this):\n"
                + rag_grounding
                + "\n\nBase your reply on this project data where relevant. Do not invent facts. "
                "Use at most one tight idea from this text — do not quote long passages."
            )

        # ── Conversation context (blind opening enforced here) ────────────────
        conversation_context = self._build_conversation_context(
            messages_ordered, participants, next_speaker_id,
        )

        turn_number = self._round_turn_number(persona_count_before, num_participants)

        is_first_turn_for_agent = not any(
            m.persona_id == next_speaker_id
            for m in simulation.messages
            if not getattr(m, "is_human_message", False) and m.persona_id is not None
        )
        # Final-round prompt only while still inside the last configured round (not when it has already finished).
        is_final_round = completed_before >= max(0, simulation.max_turns - 1)
        other_names = [p.name for pid, p in participants.items() if pid != next_speaker_id]

        turn_prompt = self._build_turn_prompt(
            simulation=simulation,
            is_first_turn_for_agent=is_first_turn_for_agent,
            is_last_facilitator=is_last_facilitator,
            last_facilitator_content=last_facilitator_content,
            other_participant_names=other_names,
            is_final_round=is_final_round,
            completed_before=completed_before,
            persona_id=next_speaker_id,
        )
        conversation_context.append({"role": "user", "content": turn_prompt})

        temperature = 0.7 if is_last_facilitator else 0.95
        # Stronger anti-repetition on mid turns; slightly softer on opening/final
        frequency_penalty = 0.3 if (is_first_turn_for_agent or is_final_round) else 0.7
        presence_penalty = 0.3 if (is_first_turn_for_agent or is_final_round) else 0.55

        try:
            response = await self.client.chat.completions.create(
                **chat_completion_kwargs(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *conversation_context,
                    ],
                    temperature=temperature,
                    max_tokens=self._max_output_tokens(),
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                )
            )

            content = response.choices[0].message.content
            # Count completion only (prompt is huge; total_tokens would hit caps in ~1–2 turns)
            if response.usage and response.usage.completion_tokens is not None:
                tokens_used = response.usage.completion_tokens
            else:
                tokens_used = estimate_tokens(content)

            message = SimulationMessage(
                simulation_id=simulation.id,
                persona_id=next_speaker_id,
                content=content,
                turn_number=turn_number,
                tokens=tokens_used,
            )
            session.add(message)

            persona_count_after = persona_count_before + 1
            completed_after = self._completed_full_rounds(persona_count_after, num_participants)
            simulation.current_turn = completed_after
            simulation.tokens_used += tokens_used

            for p in simulation.participants:
                if p.persona_id == next_speaker_id:
                    p.messages_count += 1
                    p.tokens_used    += tokens_used
                    break

            # Stop only after max_turns full rounds are completed (every persona spoke each round).
            if completed_after >= simulation.max_turns:
                simulation.status = "completed"
                simulation.completed_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(message)
            return message

        except Exception as e:
            logger.error(f"Error generating turn for simulation {simulation.id}: {e}", exc_info=True)
            raise

    # ──────────────────────────────────────────────────────────────────────────
    # Static helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _count_persona_messages(messages: List[SimulationMessage]) -> int:
        return sum(
            1 for m in messages
            if m.persona_id is not None and not getattr(m, "is_human_message", False)
        )

    @staticmethod
    def _round_turn_number(persona_message_count: int, num_participants: int) -> int:
        if num_participants <= 0:
            return 1
        return max(1, (persona_message_count + num_participants) // num_participants)

    @staticmethod
    def _completed_full_rounds(persona_message_count: int, num_participants: int) -> int:
        """How many full rounds (every persona spoke once) are finished."""
        if num_participants <= 0:
            return 0
        return persona_message_count // num_participants

    @staticmethod
    def _chronological_messages(messages: List[SimulationMessage]) -> List[SimulationMessage]:
        """True speak order: by id (turn_number alone is not unique within a round)."""
        return sorted(messages or [], key=lambda m: (m.id is None, m.id or 0))

    @staticmethod
    def _persona_display_name(persona: Optional[Persona]) -> str:
        if not persona:
            return ""
        pd = persona.persona_data or {}
        return str(pd.get("name") or persona.name or "").strip()

    @classmethod
    def _addressed_persona_id(
        cls,
        facilitator_text: str,
        participant_ids: List[int],
        participants: Optional[Dict[int, Persona]],
    ) -> Optional[int]:
        """
        If the facilitator named / @mentioned a participant, return that persona id.
        Longest name match wins so "Amina Khan" beats "Amina".
        """
        if not facilitator_text or not participants:
            return None
        text = facilitator_text.strip()
        if not text:
            return None

        candidates: List[Tuple[int, str]] = []
        for pid in participant_ids:
            name = cls._persona_display_name(participants.get(pid))
            if name:
                candidates.append((pid, name))
        # Longest first to avoid partial overlaps
        candidates.sort(key=lambda x: len(x[1]), reverse=True)

        lowered = text.lower()
        for pid, name in candidates:
            n = name.lower()
            # @Name or @FirstName
            if re.search(r"@" + re.escape(n) + r"\b", lowered):
                return pid
            # Name at start: "Bilal, …" / "Bilal —" / "Bilal:"
            if re.match(re.escape(n) + r"\b\s*[,:\-—–]", lowered):
                return pid
            # "to Bilal" / "ask Bilal" / "Bilal should" / speaking to Bilal
            if re.search(
                r"\b(?:to|ask|asking|for|addressing|calling on|@)\s+"
                + re.escape(n)
                + r"\b",
                lowered,
            ):
                return pid
            # Bare full name anywhere (prefer full names; first-name-only only if unique)
            if " " in n and re.search(r"\b" + re.escape(n) + r"\b", lowered):
                return pid

        # First-name / single-token fallback when unique among participants
        first_names: Dict[str, List[int]] = {}
        for pid, name in candidates:
            first = name.split()[0].lower()
            first_names.setdefault(first, []).append(pid)
        for first, pids in first_names.items():
            if len(pids) != 1:
                continue
            if re.match(re.escape(first) + r"\b\s*[,:\-—–]", lowered):
                return pids[0]
            if re.search(
                r"\b(?:to|ask|asking|for|addressing|calling on|@)\s+"
                + re.escape(first)
                + r"\b",
                lowered,
            ):
                return pids[0]
            if re.search(r"\b" + re.escape(first) + r"\b", lowered):
                return pids[0]
        return None

    def _select_next_speaker(
        self,
        messages: List[SimulationMessage],
        participant_ids: List[int],
        current_turn: int,
        participants: Optional[Dict[int, Persona]] = None,
    ) -> int:
        """
        Round-robin with load balancing.

        If the latest message is a facilitator intervention that addresses a
        specific persona, that persona speaks next; afterwards order continues
        from them (normal round-robin).
        """
        ordered = list(participant_ids)
        chronological = self._chronological_messages(messages)
        if not chronological:
            return ordered[0]

        last_msg = chronological[-1]
        last_is_facilitator = (
            getattr(last_msg, "is_human_message", False) or last_msg.persona_id is None
        )
        if last_is_facilitator:
            addressed = self._addressed_persona_id(
                last_msg.content or "", ordered, participants
            )
            if addressed is not None and addressed in ordered:
                return addressed

        persona_messages = [
            m for m in chronological
            if not (getattr(m, "is_human_message", False) or m.persona_id is None)
        ]
        if not persona_messages:
            return ordered[0]

        last_speaker   = persona_messages[-1].persona_id
        message_counts = {pid: 0 for pid in ordered}
        for msg in persona_messages:
            if msg.persona_id in message_counts:
                message_counts[msg.persona_id] += 1

        min_count = min(message_counts.values())
        if last_speaker in ordered:
            last_idx = ordered.index(last_speaker)
            rotation = ordered[last_idx + 1:] + ordered[:last_idx + 1]
        else:
            rotation = ordered

        without_last = [pid for pid in rotation if pid != last_speaker]
        for pid in without_last:
            if message_counts[pid] == min_count:
                return pid
        return without_last[0] if without_last else ordered[0]

    # ──────────────────────────────────────────────────────────────────────────
    # Full simulation runner
    # ──────────────────────────────────────────────────────────────────────────

    async def run_full_simulation(
        self,
        simulation: Simulation,
        session: AsyncSession,
    ) -> List[SimulationMessage]:
        """
        Run the entire simulation until completion or limits are reached.

        NOTE ON run_until_agreement:
        The agreement evaluator measures linguistic convergence. In a simulation
        of discussion designed to surface genuine disagreement, early termination
        on surface consensus is the failure mode being studied — not a success
        condition. For study corpora, set run_until_agreement=False and let the
        simulation run to max_turns so the full stance trajectory is captured.
        """
        from app.services.agreement_evaluator_service import agreement_evaluator_service

        run_until = getattr(simulation, "run_until_agreement", False)
        if run_until:
            logger.info(
                "Simulation %d: run_until_agreement=True. Agreement is evaluated and stored, "
                "but termination is still controlled only by max_turns.",
                simulation.id,
            )

        messages: List[SimulationMessage] = []
        simulation.status     = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await session.commit()

        try:
            last_evaluated_turn = 0

            while simulation.status == "running":
                await session.refresh(simulation, ["messages", "participants"])

                message = await self.generate_turn(simulation, session)
                if message:
                    messages.append(message)
                else:
                    break

                if run_until and simulation.current_turn > last_evaluated_turn:
                    last_evaluated_turn = simulation.current_turn

                    participants_map: Dict[int, Persona] = {}
                    for p in simulation.participants:
                        result = await session.execute(
                            select(Persona).where(Persona.id == p.persona_id)
                        )
                        persona = result.scalar_one_or_none()
                        if persona:
                            participants_map[p.persona_id] = persona

                    await session.refresh(simulation, ["messages"])

                    try:
                        evaluation = await agreement_evaluator_service.evaluate_agreement(
                            simulation=simulation,
                            participants=participants_map,
                            session=session,
                            turn_number=simulation.current_turn,
                        )
                        logger.info(
                            "Sim %d turn %d: agreement_score=%.3f reached=%s",
                            simulation.id,
                            simulation.current_turn,
                            evaluation.overall_agreement_score,
                            evaluation.agreement_reached,
                        )
                    except Exception as eval_err:
                        logger.warning(
                            "Agreement evaluation failed for simulation %d: %s",
                            simulation.id, eval_err, exc_info=True,
                        )

                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error running simulation {simulation.id}: {e}", exc_info=True)
            simulation.status = "stopped"
            await session.commit()
            raise

        return messages

    # ──────────────────────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────────────────────

    async def generate_summary(
        self,
        simulation: Simulation,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Generate a summary of the simulation of discussion."""
        participants: Dict[int, Persona] = {}
        for p in simulation.participants:
            result = await session.execute(select(Persona).where(Persona.id == p.persona_id))
            persona = result.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona

        transcript_parts = []
        for msg in simulation.messages:
            if getattr(msg, "is_human_message", False) or msg.persona_id is None:
                name = "Facilitator"
            else:
                persona = participants.get(msg.persona_id)
                name = persona.name if persona else "Unknown"
            transcript_parts.append(f"{name}: {msg.content}")
        transcript = "\n\n".join(transcript_parts)

        persona_entries = [
            {"persona_id": pid, "persona_name": p.name}
            for pid, p in participants.items()
        ]

        summary_prompt = f"""Analyse this group discussion and provide:

1. For each participant, a concise summary (2-3 sentences) of their key points
   and final position.
2. 3-5 points of genuine disagreement that remained unresolved.
3. 3-5 points where participants appeared to reach shared understanding.
4. 3-5 actionable recommendations or next steps.

DISCUSSION GOAL: {simulation.goal}
{f"CONTEXT: {simulation.goal_context}" if simulation.goal_context else ""}

TRANSCRIPT:
{transcript}

Respond in JSON format:
{{
  "persona_summaries": [
    {{ "persona_id": <number>, "persona_name": "<name>", "summary": "<2-3 sentences>" }},
    ...
  ],
  "unresolved_disagreements": ["disagreement 1", ...],
  "shared_understanding": ["point 1", ...],
  "action_items": ["action 1", ...]
}}"""

        try:
            response = await self.client.chat.completions.create(
                **chat_completion_kwargs(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert analyst of group discussions. "
                                "Your job is to identify where participants genuinely agree, "
                                "where they genuinely disagree, and where apparent agreement "
                                "may mask unresolved differences."
                            ),
                        },
                        {"role": "user", "content": summary_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.5,
                )
            )

            result = json.loads(response.choices[0].message.content)
            persona_summaries = result.get("persona_summaries", [])
            seen_ids = {s["persona_id"] for s in persona_summaries}
            for e in persona_entries:
                if e["persona_id"] not in seen_ids:
                    persona_summaries.append({
                        "persona_id": e["persona_id"],
                        "persona_name": e["persona_name"],
                        "summary": "No summary generated.",
                    })

            simulation.summary      = json.dumps(persona_summaries)
            simulation.key_insights = result.get("unresolved_disagreements", [])
            simulation.action_items = result.get("action_items", [])
            await session.commit()

            return {
                "persona_summaries":         persona_summaries,
                "unresolved_disagreements":  result.get("unresolved_disagreements", []),
                "shared_understanding":      result.get("shared_understanding", []),
                "action_items":              simulation.action_items,
            }

        except Exception as e:
            logger.error(f"Error generating summary for simulation {simulation.id}: {e}", exc_info=True)
            raise

    # ──────────────────────────────────────────────────────────────────────────
    # Streaming
    # ──────────────────────────────────────────────────────────────────────────

    async def stream_turn(
        self,
        simulation: Simulation,
        session: AsyncSession,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a turn response for real-time updates."""
        if simulation.status in ("completed", "stopped"):
            yield {"type": "error", "message": "Simulation is not active"}
            return

        participants: Dict[int, Persona] = {}
        participant_roles: Dict[int, Optional[str]] = {}
        for p in simulation.participants:
            result = await session.execute(select(Persona).where(Persona.id == p.persona_id))
            persona = result.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona
                participant_roles[p.persona_id] = p.role

        if not participants:
            yield {"type": "error", "message": "No valid participants"}
            return

        participant_ids = [
            p.persona_id
            for p in sorted(simulation.participants, key=lambda sp: sp.id or 0)
            if p.persona_id in participants
        ] or list(participants.keys())

        num_participants = len(participant_ids)
        persona_count_before = self._count_persona_messages(list(simulation.messages))
        completed_before = self._completed_full_rounds(persona_count_before, num_participants)
        if completed_before >= simulation.max_turns:
            simulation.status = "completed"
            simulation.completed_at = datetime.now(timezone.utc)
            simulation.current_turn = completed_before
            await session.commit()
            yield {
                "type": "complete",
                "reason": "max_turns_reached",
                "simulation_status": simulation.status,
                "current_turn": simulation.current_turn,
                "tokens_used": simulation.tokens_used,
            }
            return

        next_speaker_id = self._select_next_speaker(
            self._chronological_messages(list(simulation.messages)),
            participant_ids,
            simulation.current_turn,
            participants=participants,
        )
        next_persona = participants[next_speaker_id]
        next_role    = participant_roles.get(next_speaker_id)

        turn_number      = self._round_turn_number(persona_count_before, num_participants)

        yield {
            "type":         "start",
            "persona_id":   next_speaker_id,
            "persona_name": next_persona.name,
            "turn_number":  turn_number,
        }

        messages_ordered = self._chronological_messages(list(simulation.messages))
        last_facilitator_content, is_last_facilitator = self._get_facilitator_context(
            messages_ordered
        )
        facilitator_must_address = last_facilitator_content if is_last_facilitator else None

        system_prompt = self._build_persona_system_prompt(
            next_persona,
            next_role,
            facilitator_must_address=facilitator_must_address,
        )
        rag_grounding = await self._get_rag_grounding(
            session, simulation, messages_ordered, participants
        )
        if rag_grounding:
            system_prompt += (
                "\n\nGROUNDING — EVIDENCE FROM PROJECT DOCUMENTS (use this):\n"
                + rag_grounding
                + "\n\nBase your reply on this project data where relevant. Do not invent facts. "
                "Use at most one tight idea from this text — do not quote long passages."
            )

        conversation_context = self._build_conversation_context(
            messages_ordered, participants, next_speaker_id,
        )

        is_first_turn_for_agent = not any(
            m.persona_id == next_speaker_id
            for m in simulation.messages
            if not getattr(m, "is_human_message", False) and m.persona_id is not None
        )
        is_final_round = completed_before >= max(0, simulation.max_turns - 1)
        other_names    = [p.name for pid, p in participants.items() if pid != next_speaker_id]

        turn_prompt = self._build_turn_prompt(
            simulation=simulation,
            is_first_turn_for_agent=is_first_turn_for_agent,
            is_last_facilitator=is_last_facilitator,
            last_facilitator_content=last_facilitator_content,
            other_participant_names=other_names,
            is_final_round=is_final_round,
            completed_before=completed_before,
            persona_id=next_speaker_id,
        )
        conversation_context.append({"role": "user", "content": turn_prompt})

        temperature = 0.7 if is_last_facilitator else 0.95
        frequency_penalty = 0.3 if (is_first_turn_for_agent or is_final_round) else 0.7
        presence_penalty = 0.3 if (is_first_turn_for_agent or is_final_round) else 0.55
        full_content = ""

        try:
            stream = await self.client.chat.completions.create(
                **chat_completion_kwargs(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *conversation_context,
                    ],
                    temperature=temperature,
                    max_tokens=self._max_output_tokens(),
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    stream=True,
                )
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {"type": "chunk", "content": content}

            tokens_used = estimate_tokens(full_content)
            message = SimulationMessage(
                simulation_id=simulation.id,
                persona_id=next_speaker_id,
                content=full_content,
                turn_number=turn_number,
                tokens=tokens_used,
            )
            session.add(message)

            persona_count_after = persona_count_before + 1
            completed_after = self._completed_full_rounds(persona_count_after, num_participants)
            simulation.current_turn = completed_after
            simulation.tokens_used += tokens_used

            for p in simulation.participants:
                if p.persona_id == next_speaker_id:
                    p.messages_count += 1
                    p.tokens_used    += tokens_used
                    break

            if completed_after >= simulation.max_turns:
                simulation.status = "completed"
                simulation.completed_at = datetime.now(timezone.utc)

            await session.commit()

            yield {
                "type":              "complete",
                "message_id":        message.id,
                "content":           full_content,
                "tokens":            tokens_used,
                "simulation_status": simulation.status,
                "current_turn":      simulation.current_turn,
                "tokens_used":       simulation.tokens_used,
            }

        except Exception as e:
            logger.error(f"Error streaming turn: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}


# ─── Global service instance ───────────────────────────────────────────────────
simulation_service = PersonaSimulationService()