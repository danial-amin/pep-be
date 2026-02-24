"""
Persona Simulation Service - orchestrates multi-persona LLM conversations.

This service enables multiple persona-infused LLMs to converse with each other
towards a common goal, with configurable duration and token limits.
"""
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
import json
import logging
import asyncio

from app.core.config import settings
from app.core.vector_db import vector_db
from app.models.simulation import Simulation, SimulationParticipant, SimulationMessage
from app.utils.rag_filter import get_project_document_filter
from app.models.persona import Persona
from app.utils.token_utils import estimate_tokens

logger = logging.getLogger(__name__)


class PersonaSimulationService:
    """Service for running multi-persona simulations."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _build_persona_system_prompt(
        self,
        persona: Persona,
        role: Optional[str] = None,
        facilitator_must_address: Optional[str] = None,
    ) -> str:
        """Build a system prompt that infuses the LLM with the persona's personality."""
        persona_data = persona.persona_data or {}

        # Extract key persona attributes
        name = persona_data.get("name", persona.name)
        demographics = persona_data.get("demographics", {})
        background = persona_data.get("background", "")
        goals = persona_data.get("goals", [])
        frustrations = persona_data.get("frustrations", [])
        motivations = persona_data.get("motivations", [])
        behaviors = persona_data.get("behaviors", "")
        quote = persona_data.get("quote", "")

        # Build demographic string
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

        # Format goals and frustrations
        goals_str = "\n".join([f"  - {g}" for g in goals]) if goals else "  - Not specified"
        frustrations_str = "\n".join([f"  - {f}" for f in frustrations]) if frustrations else "  - Not specified"
        motivations_str = "\n".join([f"  - {m}" for m in motivations]) if motivations else ""

        role_instruction = ""
        if role:
            role_instruction = f"\n\nYour assigned role in this discussion is: {role}. Act according to this role while staying true to your persona."

        system_prompt = f"""You are {name}, {demographic_str}.

BACKGROUND:
{background}

YOUR GOALS:
{goals_str}

YOUR FRUSTRATIONS AND PAIN POINTS:
{frustrations_str}

{"YOUR MOTIVATIONS:" if motivations_str else ""}
{motivations_str}

{"BEHAVIORAL TRAITS:" if behaviors else ""}
{behaviors}

{"CHARACTERISTIC QUOTE: " + '"' + quote + '"' if quote else ""}
{role_instruction}

CONVERSATION GUIDELINES:
- Respond authentically as this persona would, drawing from their background, goals, and frustrations
- Share insights and perspectives that reflect your unique experiences and viewpoint
- Engage constructively with others while maintaining your persona's authentic voice
- Be specific and concrete when possible, relating ideas to your personal experience
- Keep responses focused and concise (1-3 sentences, ~60 words max)
- Build on what others say, agree or respectfully disagree based on your persona's perspective
- If you have expertise relevant to the topic, share it naturally
- Express your frustrations and concerns when relevant to the discussion"""

        if facilitator_must_address:
            system_prompt += f"""

CRITICAL - FACILITATOR INTERVENTION (you must obey this):
A human facilitator has just intervened and said: "{facilitator_must_address}"
You MUST address this directly in your very next response and let it change the course of your reply. Do not ignore it or continue the previous thread without first acknowledging and responding to the facilitator. Your response should visibly shift to incorporate their direction."""

        return system_prompt

    async def _get_rag_grounding(
        self,
        session: AsyncSession,
        simulation: Simulation,
        messages_ordered: List[SimulationMessage],
        participants: Dict[int, Persona],
    ) -> str:
        """
        Retrieve relevant document chunks from RAG so simulation responses are grounded in project data.
        Uses document_id filter (not project_id) so we only get chunks from the project's files.
        Returns a single string of concatenated chunks to inject into the prompt; empty if none.
        """
        # Build query from goal + context + last few persona messages for relevance
        query_parts = [simulation.goal]
        if simulation.goal_context:
            query_parts.append(simulation.goal_context)
        persona_msgs = [
            m for m in messages_ordered
            if not (getattr(m, "is_human_message", False) or m.persona_id is None)
        ]
        for m in persona_msgs[-3:]:  # last 3 persona messages
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
            # Dedupe and join with clear separators; cap total length for context window
            seen = set()
            unique = []
            total = 0
            max_chars = 6000
            for c in chunks:
                if c and c not in seen and total + len(c) <= max_chars:
                    seen.add(c)
                    unique.append(c)
                    total += len(c)
            if not unique:
                return ""
            return "\n\n---\n\n".join(unique)
        except Exception as e:
            logger.warning(f"RAG grounding failed for simulation {simulation.id}: {e}", exc_info=True)
            return ""

    def _get_facilitator_context(
        self, messages: List[SimulationMessage]
    ) -> tuple[Optional[str], bool]:
        """
        Returns (last_facilitator_content, is_last_message_facilitator).
        Used to steer the simulation when a human has intervened.
        """
        msgs = sorted(messages, key=lambda m: (m.turn_number, m.id))
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

    def _build_conversation_context(
        self,
        messages: List[SimulationMessage],
        participants: Dict[int, Persona],
        current_persona_id: int
    ) -> List[Dict[str, str]]:
        """Build the conversation history for the LLM context."""
        context = []

        for msg in messages:
            is_human = getattr(msg, "is_human_message", False) or msg.persona_id is None
            if is_human:
                # Human facilitator intervention - always as user message, highlighted
                context.append({
                    "role": "user",
                    "content": f"[Facilitator]: {msg.content}"
                })
                continue

            persona = participants.get(msg.persona_id)
            persona_name = persona.name if persona else "Unknown"

            if msg.persona_id == current_persona_id:
                # This persona's own messages
                context.append({
                    "role": "assistant",
                    "content": msg.content
                })
            else:
                # Other persona's messages - format as user message with name
                context.append({
                    "role": "user",
                    "content": f"[{persona_name}]: {msg.content}"
                })

        return context

    async def generate_turn(
        self,
        simulation: Simulation,
        session: AsyncSession
    ) -> Optional[SimulationMessage]:
        """
        Generate the next turn in the simulation.

        Selects the next persona to speak based on conversation flow
        and generates their response.
        """
        # Check if simulation can continue
        if simulation.status == "completed" or simulation.status == "stopped":
            return None

        # Check turn limit
        if simulation.current_turn >= simulation.max_turns:
            simulation.status = "completed"
            simulation.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return None

        # Check duration limit
        if simulation.started_at and simulation.max_duration_seconds:
            elapsed = (datetime.now(timezone.utc) - simulation.started_at).total_seconds()
            if elapsed >= simulation.max_duration_seconds:
                simulation.status = "completed"
                simulation.completed_at = datetime.now(timezone.utc)
                await session.commit()
                return None

        # Get participants and their personas
        participants = {}
        participant_roles = {}
        for p in simulation.participants:
            result = await session.execute(
                select(Persona).where(Persona.id == p.persona_id)
            )
            persona = result.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona
                participant_roles[p.persona_id] = p.role

        if not participants:
            logger.error(f"No valid participants for simulation {simulation.id}")
            return None

        # Select next speaker
        next_speaker_id = self._select_next_speaker(
            list(simulation.messages),
            list(participants.keys()),
            simulation.current_turn
        )

        next_persona = participants[next_speaker_id]
        next_role = participant_roles.get(next_speaker_id)

        # Facilitator context: so the next turn actually changes course when human intervened
        messages_ordered = sorted(
            simulation.messages,
            key=lambda m: (m.turn_number, getattr(m, "id", 0)),
        )
        last_facilitator_content, is_last_facilitator = self._get_facilitator_context(
            messages_ordered
        )

        # Build system prompt: inject facilitator directive when they just intervened
        facilitator_must_address = (
            last_facilitator_content if is_last_facilitator else None
        )
        system_prompt = self._build_persona_system_prompt(
            next_persona, next_role, facilitator_must_address=facilitator_must_address
        )

        # RAG grounding: inject evidence from project documents so responses are grounded, not made up
        rag_grounding = await self._get_rag_grounding(
            session, simulation, messages_ordered, participants
        )
        if rag_grounding:
            system_prompt += (
                "\n\nGROUNDING — EVIDENCE FROM PROJECT DOCUMENTS (you must use this):\n"
                + rag_grounding
                + "\n\nYour response must be grounded in the above evidence. Do not invent facts; base your reply on this project data when relevant."
            )

        # Build conversation context
        conversation_context = self._build_conversation_context(
            messages_ordered,
            participants,
            next_speaker_id,
        )

        # Add the goal and initial prompt if no persona has spoken yet (round 0)
        persona_count_before = self._count_persona_messages(list(simulation.messages))
        if persona_count_before == 0:
            goal_prompt = f"""The topic for this group discussion is: {simulation.goal}

{simulation.goal_context if simulation.goal_context else ""}

Please share your initial thoughts on this topic, drawing from your personal experience and perspective. Be authentic to who you are."""
            conversation_context.append({"role": "user", "content": goal_prompt})
        else:
            # When facilitator just intervened: strong prompt so the simulation changes course
            if is_last_facilitator and last_facilitator_content:
                continue_prompt = f"""The facilitator has just intervened: "{last_facilitator_content}"

Your response MUST:
1. First, directly acknowledge and respond to what the facilitator said.
2. Then, let their direction change the course of your reply (e.g. shift focus, address their question, or incorporate their suggestion).
Keep it to 1-3 sentences but make the course change visible."""
            elif last_facilitator_content:
                # Recent facilitator intervention (not last message): remind to keep that direction
                continue_prompt = f"""Continue the discussion. The facilitator recently said: "{last_facilitator_content}" — keep this direction in mind and let it influence your response. Share your perspective in 1-3 sentences."""
            else:
                continue_prompt = "Please continue the discussion by responding to what has been said. Share your perspective, agree or disagree, and add new insights based on your experience. Keep it to 1-3 sentences."
            conversation_context.append({"role": "user", "content": continue_prompt})

        # Slightly lower temperature when facilitator just intervened so model follows instructions
        temperature = 0.65 if is_last_facilitator else 0.85

        # Generate response
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *conversation_context
                ],
                temperature=temperature,
                max_tokens=180,  # Keep individual responses concise
                presence_penalty=0.3,
                frequency_penalty=0.3
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else estimate_tokens(content)

            # One turn = all personas have spoken once; assign round-based turn number
            persona_count = self._count_persona_messages(list(simulation.messages))
            num_participants = len(participants)
            turn_number = self._round_turn_number(persona_count, num_participants)

            # Create message
            message = SimulationMessage(
                simulation_id=simulation.id,
                persona_id=next_speaker_id,
                content=content,
                turn_number=turn_number,
                tokens=tokens_used
            )
            session.add(message)

            # Update simulation state: current_turn = round (1 turn = all personas spoke once)
            simulation.current_turn = turn_number
            simulation.tokens_used += tokens_used

            # Update participant stats
            for p in simulation.participants:
                if p.persona_id == next_speaker_id:
                    p.messages_count += 1
                    p.tokens_used += tokens_used
                    break

            # Check if we should complete
            if simulation.current_turn >= simulation.max_turns or simulation.tokens_used >= simulation.max_tokens:
                simulation.status = "completed"
                simulation.completed_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(message)

            return message

        except Exception as e:
            logger.error(f"Error generating turn for simulation {simulation.id}: {e}", exc_info=True)
            raise

    @staticmethod
    def _count_persona_messages(messages: List[SimulationMessage]) -> int:
        """Count messages from personas only (exclude human interventions)."""
        return sum(
            1 for m in messages
            if m.persona_id is not None and not getattr(m, "is_human_message", False)
        )

    @staticmethod
    def _round_turn_number(persona_message_count: int, num_participants: int) -> int:
        """
        Compute turn (round) number: 1 turn = all personas have spoken once.
        For the next persona message (the (persona_message_count+1)-th), returns which round it belongs to.
        """
        if num_participants <= 0:
            return 1
        return max(1, (persona_message_count + num_participants) // num_participants)

    def _select_next_speaker(
        self,
        messages: List[SimulationMessage],
        participant_ids: List[int],
        current_turn: int
    ) -> int:
        """
        Select the next persona to speak.

        Uses a round-robin approach with some variation to keep
        the conversation dynamic. Human interventions are ignored
        for speaker selection (only persona messages count).
        """
        ordered_participants = list(participant_ids)
        persona_messages = [
            m for m in messages
            if not (getattr(m, "is_human_message", False) or m.persona_id is None)
        ]

        if not persona_messages:
            # First turn or only human messages so far - pick first participant
            return ordered_participants[0]

        # Get the last persona speaker (ignore human interventions)
        last_speaker = persona_messages[-1].persona_id

        # Count messages per participant (persona messages only)
        message_counts = {pid: 0 for pid in ordered_participants}
        for msg in persona_messages:
            if msg.persona_id in message_counts:
                message_counts[msg.persona_id] += 1

        # Prefer least-spoken, but maintain a strict rotation order
        min_count = min(message_counts.values())
        if last_speaker in ordered_participants:
            last_idx = ordered_participants.index(last_speaker)
            rotation = ordered_participants[last_idx + 1:] + ordered_participants[:last_idx + 1]
        else:
            rotation = ordered_participants

        rotation_without_last = [pid for pid in rotation if pid != last_speaker]
        for pid in rotation_without_last:
            if message_counts[pid] == min_count:
                return pid

        # Fallback: next in rotation, avoiding immediate repeat if possible
        if rotation_without_last:
            return rotation_without_last[0]

        return ordered_participants[0]

    async def run_full_simulation(
        self,
        simulation: Simulation,
        session: AsyncSession
    ) -> List[SimulationMessage]:
        """
        Run the entire simulation until completion or limits are reached.

        Stops when either:
        - max_turns is reached
        - max_duration_seconds has elapsed
        """
        messages = []

        # Start the simulation
        simulation.status = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await session.commit()

        try:
            while simulation.status == "running":
                # Check duration limit before each turn
                if simulation.max_duration_seconds:
                    elapsed = (datetime.now(timezone.utc) - simulation.started_at).total_seconds()
                    if elapsed >= simulation.max_duration_seconds:
                        simulation.status = "completed"
                        simulation.completed_at = datetime.now(timezone.utc)
                        await session.commit()
                        break

                # Refresh to get latest state
                await session.refresh(simulation, ["messages", "participants"])

                message = await self.generate_turn(simulation, session)
                if message:
                    messages.append(message)
                else:
                    break

                # Small delay between turns for rate limiting
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error running simulation {simulation.id}: {e}", exc_info=True)
            simulation.status = "stopped"
            await session.commit()
            raise

        return messages

    async def generate_summary(
        self,
        simulation: Simulation,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Generate a summary of the simulation conversation.

        Extracts key insights and action items.
        """
        # Get participants for names
        participants = {}
        for p in simulation.participants:
            result = await session.execute(
                select(Persona).where(Persona.id == p.persona_id)
            )
            persona = result.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona

        # Build conversation transcript
        transcript_parts = []
        for msg in simulation.messages:
            if getattr(msg, "is_human_message", False) or msg.persona_id is None:
                name = "Facilitator"
            else:
                persona = participants.get(msg.persona_id)
                name = persona.name if persona else "Unknown"
            transcript_parts.append(f"{name}: {msg.content}")

        transcript = "\n\n".join(transcript_parts)

        # Persona names and ids for per-persona summary text
        persona_entries = [
            {"persona_id": pid, "persona_name": p.name}
            for pid, p in participants.items()
        ]

        # Generate summary as before: per-persona summary text + overall key_insights and action_items
        summary_prompt = f"""Analyze this group discussion and provide:

1. For each participant, a concise summary (2-3 sentences) of that person's key points and stance.
2. 3-5 key insights that emerged from the conversation overall.
3. 3-5 actionable recommendations or next steps overall.

DISCUSSION GOAL: {simulation.goal}
{f"CONTEXT: {simulation.goal_context}" if simulation.goal_context else ""}

TRANSCRIPT:
{transcript}

Respond in JSON format:
{{
  "persona_summaries": [
    {{ "persona_id": <number>, "persona_name": "<name>", "summary": "<2-3 sentences for this persona>" }},
    ...
  ],
  "key_insights": ["insight 1", "insight 2", ...],
  "action_items": ["action 1", "action 2", ...]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert facilitator skilled at synthesizing group discussions into actionable insights."
                    },
                    {"role": "user", "content": summary_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )

            result = json.loads(response.choices[0].message.content)
            persona_summaries = result.get("persona_summaries", [])
            seen_ids = {s["persona_id"] for s in persona_summaries}
            for e in persona_entries:
                if e["persona_id"] not in seen_ids:
                    persona_summaries.append({
                        "persona_id": e["persona_id"],
                        "persona_name": e["persona_name"],
                        "summary": "No summary generated."
                    })

            simulation.summary = json.dumps(persona_summaries)
            simulation.key_insights = result.get("key_insights", [])
            simulation.action_items = result.get("action_items", [])
            await session.commit()

            return {
                "persona_summaries": persona_summaries,
                "key_insights": simulation.key_insights,
                "action_items": simulation.action_items,
            }

        except Exception as e:
            logger.error(f"Error generating summary for simulation {simulation.id}: {e}", exc_info=True)
            raise

    async def stream_turn(
        self,
        simulation: Simulation,
        session: AsyncSession
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a turn response for real-time updates.

        Yields chunks of the response as they're generated.
        """
        # Check if simulation can continue
        if simulation.status in ["completed", "stopped"]:
            yield {"type": "error", "message": "Simulation is not active"}
            return

        if simulation.current_turn >= simulation.max_turns:
            simulation.status = "completed"
            simulation.completed_at = datetime.now(timezone.utc)
            await session.commit()
            yield {
                "type": "complete",
                "reason": "max_turns_reached",
                "simulation_status": simulation.status,
                "current_turn": simulation.current_turn,
                "tokens_used": simulation.tokens_used
            }
            return

        if simulation.tokens_used >= simulation.max_tokens:
            simulation.status = "completed"
            simulation.completed_at = datetime.now(timezone.utc)
            await session.commit()
            yield {
                "type": "complete",
                "reason": "max_tokens_reached",
                "simulation_status": simulation.status,
                "current_turn": simulation.current_turn,
                "tokens_used": simulation.tokens_used
            }
            return

        # Get participants
        participants = {}
        participant_roles = {}
        for p in simulation.participants:
            result = await session.execute(
                select(Persona).where(Persona.id == p.persona_id)
            )
            persona = result.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona
                participant_roles[p.persona_id] = p.role

        # Select next speaker
        next_speaker_id = self._select_next_speaker(
            list(simulation.messages),
            list(participants.keys()),
            simulation.current_turn
        )

        next_persona = participants[next_speaker_id]
        next_role = participant_roles.get(next_speaker_id)

        # One turn = all personas have spoken once
        persona_count = self._count_persona_messages(list(simulation.messages))
        num_participants = len(participants)
        turn_number = self._round_turn_number(persona_count, num_participants)

        yield {
            "type": "start",
            "persona_id": next_speaker_id,
            "persona_name": next_persona.name,
            "turn_number": turn_number
        }

        # Facilitator context: so the next turn actually changes course when human intervened
        messages_ordered = sorted(
            simulation.messages,
            key=lambda m: (m.turn_number, getattr(m, "id", 0)),
        )
        last_facilitator_content, is_last_facilitator = self._get_facilitator_context(
            messages_ordered
        )
        facilitator_must_address = (
            last_facilitator_content if is_last_facilitator else None
        )

        # Build prompts: inject facilitator directive when they just intervened
        system_prompt = self._build_persona_system_prompt(
            next_persona, next_role, facilitator_must_address=facilitator_must_address
        )
        # RAG grounding: evidence from project documents
        rag_grounding = await self._get_rag_grounding(
            session, simulation, messages_ordered, participants
        )
        if rag_grounding:
            system_prompt += (
                "\n\nGROUNDING — EVIDENCE FROM PROJECT DOCUMENTS (you must use this):\n"
                + rag_grounding
                + "\n\nYour response must be grounded in the above evidence. Do not invent facts; base your reply on this project data when relevant."
            )
        conversation_context = self._build_conversation_context(
            messages_ordered,
            participants,
            next_speaker_id,
        )

        if persona_count == 0:
            goal_prompt = f"""The topic for this group discussion is: {simulation.goal}

{simulation.goal_context if simulation.goal_context else ""}

Please share your initial thoughts on this topic, drawing from your personal experience and perspective."""
            conversation_context.append({"role": "user", "content": goal_prompt})
        else:
            if is_last_facilitator and last_facilitator_content:
                continue_prompt = f"""The facilitator has just intervened: "{last_facilitator_content}"

Your response MUST: 1) First, directly acknowledge and respond to what the facilitator said. 2) Let their direction change the course of your reply. Keep it to 1-3 sentences but make the course change visible."""
            elif last_facilitator_content:
                continue_prompt = f"""Continue the discussion. The facilitator recently said: "{last_facilitator_content}" — keep this direction in mind. Share your perspective in 1-3 sentences."""
            else:
                continue_prompt = "Please continue the discussion by responding to what has been said. Keep it to 1-3 sentences."
            conversation_context.append({"role": "user", "content": continue_prompt})

        # Slightly lower temperature when facilitator just intervened
        temperature = 0.65 if is_last_facilitator else 0.85

        # Stream response
        full_content = ""
        try:
            stream = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *conversation_context
                ],
                temperature=temperature,
                max_tokens=180,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {
                        "type": "chunk",
                        "content": content
                    }

            # Save the message (turn_number already computed above)
            tokens_used = estimate_tokens(full_content)
            message = SimulationMessage(
                simulation_id=simulation.id,
                persona_id=next_speaker_id,
                content=full_content,
                turn_number=turn_number,
                tokens=tokens_used
            )
            session.add(message)

            simulation.current_turn = turn_number
            simulation.tokens_used += tokens_used

            for p in simulation.participants:
                if p.persona_id == next_speaker_id:
                    p.messages_count += 1
                    p.tokens_used += tokens_used
                    break

            if simulation.current_turn >= simulation.max_turns or simulation.tokens_used >= simulation.max_tokens:
                simulation.status = "completed"
                simulation.completed_at = datetime.now(timezone.utc)

            await session.commit()

            yield {
                "type": "complete",
                "message_id": message.id,
                "tokens": tokens_used,
                "simulation_status": simulation.status,
                "current_turn": simulation.current_turn,
                "tokens_used": simulation.tokens_used
            }

        except Exception as e:
            logger.error(f"Error streaming turn: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}


# Global service instance
simulation_service = PersonaSimulationService()
