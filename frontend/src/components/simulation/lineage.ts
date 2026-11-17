import type { AgreementEvaluation, SimulationMessage } from '../../types';

export type NodeSelection = number | 'root';

export function isPersonaMessage(message: SimulationMessage): boolean {
  return message.persona_id != null && !message.is_human_message;
}

/** Messages from the first child of the root through headId, in speak order. */
export function lineageOf(
  messages: SimulationMessage[],
  headId: number | null | undefined,
): SimulationMessage[] {
  if (headId == null) return [];
  const byId = new Map<number, SimulationMessage>();
  for (const message of messages) {
    if (message.id != null) byId.set(message.id, message);
  }
  if (!byId.has(headId)) return [];

  const chain: SimulationMessage[] = [];
  const seen = new Set<number>();
  let current: number | null | undefined = headId;
  while (current != null && !seen.has(current)) {
    seen.add(current);
    const message = byId.get(current);
    if (!message) break;
    chain.push(message);
    current = message.parent_message_id ?? null;
  }
  chain.reverse();
  return chain;
}

export function childrenByParent(messages: SimulationMessage[]): Map<number | 'root', SimulationMessage[]> {
  const map = new Map<number | 'root', SimulationMessage[]>();
  const ordered = [...messages].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
  for (const message of ordered) {
    const parent: number | 'root' = message.parent_message_id ?? 'root';
    const list = map.get(parent) ?? [];
    list.push(message);
    map.set(parent, list);
  }
  return map;
}

export function descendantCount(
  id: number | 'root',
  children: Map<number | 'root', SimulationMessage[]>,
): number {
  const kids = children.get(id) ?? [];
  return kids.reduce((sum, child) => sum + 1 + descendantCount(child.id, children), 0);
}

export function pathIsClosed(options: {
  messages: SimulationMessage[];
  headId: number | null | undefined;
  numParticipants: number;
  maxTurns: number;
  maxTokens?: number | null;
  runUntilAgreement?: boolean;
  evaluations?: AgreementEvaluation[];
}): boolean {
  const lineage = lineageOf(options.messages, options.headId);
  const personaCount = lineage.filter(isPersonaMessage).length;
  if (
    options.numParticipants > 0 &&
    options.maxTurns > 0 &&
    Math.floor(personaCount / options.numParticipants) >= options.maxTurns
  ) {
    return true;
  }
  if (options.maxTokens && lineage.length > 0) {
    const used = lineage.reduce((sum, message) => sum + (message.tokens || 0), 0);
    if (used >= options.maxTokens) return true;
  }
  if (options.runUntilAgreement && options.headId != null) {
    const reached = (options.evaluations ?? []).some(
      (evaluation) => evaluation.agreement_reached && evaluation.head_message_id === options.headId,
    );
    if (reached) return true;
  }
  return false;
}

export function agreementForHead(
  evaluations: AgreementEvaluation[] | undefined,
  headId: number | null,
): AgreementEvaluation | undefined {
  if (headId == null || !evaluations?.length) return undefined;
  const matches = evaluations.filter((evaluation) => evaluation.head_message_id === headId);
  if (!matches.length) return undefined;
  return matches[matches.length - 1];
}
