import { useState } from 'react';
import {
  Activity,
  BarChart3,
  Download,
  FileText,
  Loader2,
  Pause,
  Play,
  SkipForward,
  TrendingUp,
  Users,
} from 'lucide-react';
import { getPersonaImageUrl } from '../../utils/imageUtils';
import type { Simulation, SimulationParticipant } from '../../types';

interface PlaygroundSessionBarProps {
  simulation: Simulation;
  roundsOnPath: number;
  isStudyMode: boolean;
  running: boolean;
  streamingEnabled: boolean;
  autoContinue: boolean;
  evaluatingAgreement: boolean;
  evaluatingDiscussion: boolean;
  generatingSummary: boolean;
  showAgreementHistory: boolean;
  showEvaluationScores: boolean;
  hasAgreementHistory: boolean;
  hasEvaluation: boolean;
  canScore: boolean;
  onStart: (auto: boolean) => void;
  onStop: () => void;
  onStreaming: (value: boolean) => void;
  onAutoContinue: (value: boolean) => void;
  onOpenChats: () => void;
  onEvaluateAgreement: () => void;
  onToggleAgreementHistory: () => void;
  onEvaluateDiscussion: () => void;
  onGenerateSummary: () => void;
  onToggleEvaluation: () => void;
  onDownload: () => void;
}

function CastMark({ participant }: { participant: SimulationParticipant }) {
  const [failed, setFailed] = useState(false);
  const src = getPersonaImageUrl(participant.persona_image_url, participant.persona_id);
  if (src && !failed) {
    return (
      <img
        src={src}
        alt=""
        title={participant.persona_name}
        className="h-8 w-8 rounded-full object-cover"
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <span
      title={participant.persona_name}
      className="flex h-8 w-8 items-center justify-center rounded-full bg-stone-200 text-xs font-semibold text-stone-600"
    >
      {participant.persona_name.charAt(0).toUpperCase()}
    </span>
  );
}

function statusClass(status: string): string {
  if (status === 'completed') return 'bg-green-50 text-green-700';
  if (status === 'running') return 'bg-blue-50 text-blue-700';
  if (status === 'stopped') return 'bg-red-50 text-red-600';
  return 'bg-amber-50 text-amber-700';
}

export default function PlaygroundSessionBar(props: PlaygroundSessionBarProps) {
  const { simulation } = props;
  const hasMessages = simulation.messages.length > 0;
  const canSummarize =
    props.canScore &&
    hasMessages &&
    !(simulation.persona_summaries?.length) &&
    !simulation.summary;

  return (
    <div className="glass-card rounded-2xl p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-xl font-semibold text-stone-900">{simulation.name}</h3>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusClass(simulation.status)}`}>
              {simulation.status}
            </span>
            {simulation.agreement_reached && (
              <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700">
                Agreement reached
              </span>
            )}
          </div>
          <p className="mt-1 text-sm leading-relaxed text-stone-600">{simulation.goal}</p>
          <div className="mt-3 flex items-center gap-2">
            <div className="flex -space-x-2">
              {simulation.participants.map((participant) => (
                <CastMark key={participant.id} participant={participant} />
              ))}
            </div>
            <p className="text-xs text-stone-500">
              {simulation.participants.length} seated · {props.roundsOnPath} / {simulation.max_turns} rounds on this path
              {simulation.run_until_agreement && !simulation.agreement_reached
                ? ` · closes at ${(simulation.agreement_threshold * 100).toFixed(0)}% agreement`
                : ''}
            </p>
          </div>
          {simulation.latest_agreement_score !== undefined && (
            <div className="mt-3 max-w-sm">
              <div className="mb-1 flex justify-between text-xs text-stone-500">
                <span>Agreement on this path</span>
                <span className="font-medium text-stone-800">
                  {(simulation.latest_agreement_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-stone-100">
                <div
                  className={`h-1.5 rounded-full ${simulation.agreement_reached ? 'bg-teal-500' : 'bg-stone-900'}`}
                  style={{ width: `${Math.min(simulation.latest_agreement_score * 100, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {simulation.status === 'pending' && (
            props.isStudyMode ? (
              <button
                type="button"
                onClick={() => props.onStart(false)}
                disabled={props.running}
                className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {props.running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Start
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => props.onStart(props.autoContinue)}
                  disabled={props.running}
                  className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {props.running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Run this path
                </button>
                <button
                  type="button"
                  onClick={() => props.onStart(false)}
                  disabled={props.running}
                  className="inline-flex items-center gap-2 rounded-xl bg-stone-100 px-4 py-2 text-sm font-medium text-stone-900 hover:bg-stone-200"
                >
                  <SkipForward className="h-4 w-4" />
                  One turn
                </button>
              </>
            )
          )}
          {simulation.status === 'running' && (
            <button
              type="button"
              onClick={props.onStop}
              disabled={props.running}
              className="inline-flex items-center gap-2 rounded-xl bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
            >
              <Pause className="h-4 w-4" />
              Stop session
            </button>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3 border-t border-stone-200 pt-3 sm:flex-row sm:items-center sm:justify-between">
        {!props.isStudyMode && (
          <div className="flex flex-wrap items-center gap-4 text-sm text-stone-600">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={props.streamingEnabled}
                onChange={(event) => props.onStreaming(event.target.checked)}
                className="accent-stone-900"
              />
              Stream replies
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={props.autoContinue}
                onChange={(event) => props.onAutoContinue(event.target.checked)}
                className="accent-stone-900"
              />
              Keep going
            </label>
          </div>
        )}
        <div className="flex flex-wrap gap-2 sm:ml-auto">
          <button
            type="button"
            onClick={props.onOpenChats}
            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100"
          >
            <Users className="h-3.5 w-3.5" />
            Cast chats
          </button>
          {hasMessages && (
            <button
              type="button"
              onClick={props.onEvaluateAgreement}
              disabled={props.evaluatingAgreement || props.running}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
            >
              {props.evaluatingAgreement ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Activity className="h-3.5 w-3.5" />}
              Score agreement
            </button>
          )}
          {props.hasAgreementHistory && (
            <button
              type="button"
              onClick={props.onToggleAgreementHistory}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100"
            >
              <TrendingUp className="h-3.5 w-3.5" />
              {props.showAgreementHistory ? 'Hide history' : 'Agreement history'}
            </button>
          )}
          {props.canScore && hasMessages && (
            <button
              type="button"
              onClick={props.onEvaluateDiscussion}
              disabled={props.evaluatingDiscussion}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
            >
              {props.evaluatingDiscussion ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <BarChart3 className="h-3.5 w-3.5" />}
              {props.hasEvaluation ? 'Re-score discussion' : 'Score discussion'}
            </button>
          )}
          {canSummarize && (
            <button
              type="button"
              onClick={props.onGenerateSummary}
              disabled={props.generatingSummary}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
            >
              {props.generatingSummary ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
              Summary
            </button>
          )}
          {props.hasEvaluation && (
            <button
              type="button"
              onClick={props.onToggleEvaluation}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100"
            >
              <BarChart3 className="h-3.5 w-3.5" />
              {props.showEvaluationScores ? 'Hide scores' : 'Scores'}
            </button>
          )}
          {simulation.status === 'completed' && (
            <button
              type="button"
              onClick={props.onDownload}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100"
            >
              <Download className="h-3.5 w-3.5" />
              Download
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
