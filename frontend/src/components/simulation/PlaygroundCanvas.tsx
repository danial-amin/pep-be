import { useMemo, useState } from 'react';
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { SimulationMessage } from '../../types';
import { childrenByParent, descendantCount, lineageOf, type NodeSelection } from './lineage';

type CanvasNodeData = {
  eyebrow: string;
  title: string;
  preview: string;
  kind: 'root' | 'persona' | 'intervention';
  onPath: boolean;
  forkCount: number;
  hiddenCount: number;
  onHide: () => void;
};

function CanvasNode({ data, selected }: NodeProps<Node<CanvasNodeData>>) {
  const tone =
    data.kind === 'intervention'
      ? 'border-amber-300 bg-amber-50'
      : data.kind === 'root'
        ? 'border-stone-300 bg-[#f4f1ea]'
        : 'border-stone-200 bg-white';
  const pathEdge = data.onPath ? 'border-blue-500' : '';
  const selectedRing = selected ? 'ring-2 ring-stone-900' : '';

  return (
    <div className={`w-[200px] rounded-xl border px-3 py-2 text-left ${tone} ${pathEdge} ${selectedRing}`}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-stone-400" />
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">{data.eyebrow}</span>
        {data.forkCount > 1 && (
          <span className="rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
            {data.forkCount} forks
          </span>
        )}
      </div>
      <div className="mt-0.5 truncate text-sm font-semibold text-stone-900">{data.title}</div>
      <p className="mt-1 line-clamp-2 text-xs leading-snug text-stone-600">{data.preview}</p>
      {(data.hiddenCount > 0 || data.forkCount > 0) && (
        <button
          type="button"
          className="mt-2 text-[11px] font-medium text-stone-500 hover:text-stone-900"
          onClick={(event) => {
            event.stopPropagation();
            data.onHide();
          }}
        >
          {data.hiddenCount > 0 ? `Show ${data.hiddenCount}` : 'Hide ahead'}
        </button>
      )}
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-stone-400" />
    </div>
  );
}

const nodeTypes = { canvas: CanvasNode };

interface PlaygroundCanvasProps {
  goal: string;
  messages: SimulationMessage[];
  selectedId: NodeSelection;
  onSelect: (id: NodeSelection) => void;
}

function previewText(message: SimulationMessage): string {
  const text = (message.content || '').replace(/\s+/g, ' ').trim();
  return text.length > 140 ? `${text.slice(0, 137)}…` : text || '…';
}

function toggleCollapsed(id: number | 'root', setCollapsed: (updater: (prev: Set<string>) => Set<string>) => void) {
  setCollapsed((prev) => {
    const next = new Set(prev);
    const key = String(id);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });
}

export default function PlaygroundCanvas({
  goal,
  messages,
  selectedId,
  onSelect,
}: PlaygroundCanvasProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const { nodes, edges } = useMemo(() => {
    const children = childrenByParent(messages);
    const pathIds = new Set<number | 'root'>(['root']);
    if (typeof selectedId === 'number') {
      for (const message of lineageOf(messages, selectedId)) pathIds.add(message.id);
    }

    const positions = new Map<number | 'root', { x: number; y: number }>();
    let cursor = 0;

    const place = (id: number | 'root', depth: number): number => {
      const hidden = collapsed.has(String(id));
      const kids = hidden ? [] : (children.get(id) ?? []);
      if (kids.length === 0) {
        const slot = cursor;
        cursor += 1;
        positions.set(id, { x: depth * 280, y: slot * 140 });
        return slot;
      }
      const slots = kids.map((child) => place(child.id, depth + 1));
      const mid = (slots[0] + slots[slots.length - 1]) / 2;
      positions.set(id, { x: depth * 280, y: mid * 140 });
      return mid;
    };
    place('root', 0);

    const builtNodes: Node<CanvasNodeData>[] = [];
    const builtEdges: Edge[] = [];

    const rootPos = positions.get('root') ?? { x: 0, y: 0 };
    const rootKids = children.get('root') ?? [];
    const rootHidden = descendantCount('root', children);
    builtNodes.push({
      id: 'root',
      type: 'canvas',
      position: rootPos,
      selected: selectedId === 'root',
      data: {
        eyebrow: 'Start',
        title: 'Goal',
        preview: goal || 'Simulation goal',
        kind: 'root',
        onPath: pathIds.has('root'),
        forkCount: rootKids.length,
        hiddenCount: collapsed.has('root') ? rootHidden : 0,
        onHide: () => toggleCollapsed('root', setCollapsed),
      },
    });

    const visible = new Set<number | 'root'>(['root']);
    const walk = (id: number | 'root') => {
      if (collapsed.has(String(id))) return;
      for (const child of children.get(id) ?? []) {
        visible.add(child.id);
        walk(child.id);
      }
    };
    walk('root');

    for (const message of messages) {
      if (!visible.has(message.id)) continue;
      const position = positions.get(message.id) ?? { x: 0, y: 0 };
      const human = message.is_human_message || message.persona_id == null;
      const kids = children.get(message.id) ?? [];
      const hiddenKids = collapsed.has(String(message.id)) ? descendantCount(message.id, children) : 0;
      builtNodes.push({
        id: String(message.id),
        type: 'canvas',
        position,
        selected: selectedId === message.id,
        data: {
          eyebrow: human ? `Facilitator · round ${message.turn_number}` : `Round ${message.turn_number}`,
          title: human ? 'Facilitator' : message.persona_name,
          preview: previewText(message),
          kind: human ? 'intervention' : 'persona',
          onPath: pathIds.has(message.id),
          forkCount: kids.length,
          hiddenCount: hiddenKids,
          onHide: () => toggleCollapsed(message.id, setCollapsed),
        },
      });
      const parent = message.parent_message_id == null ? 'root' : String(message.parent_message_id);
      const onPath = pathIds.has(message.id) && (message.parent_message_id == null || pathIds.has(message.parent_message_id));
      builtEdges.push({
        id: `e-${parent}-${message.id}`,
        source: parent,
        target: String(message.id),
        type: 'smoothstep',
        style: onPath
          ? { stroke: '#2563eb', strokeWidth: 2 }
          : { stroke: '#d6d3d1', strokeWidth: 1.5 },
      });
    }

    return { nodes: builtNodes, edges: builtEdges };
  }, [collapsed, goal, messages, selectedId]);

  return (
    <div className="overflow-hidden rounded-2xl border border-stone-200 bg-[#f8f7f4]">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-stone-200 px-3 py-2 text-[11px] text-stone-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-blue-500" />
          Selected path
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          Facilitator
        </span>
        <span>A thread reads left to right. A fork opens another row.</span>
      </div>
      <div className="h-[640px]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onInit={(instance) => {
            void instance.fitView({ padding: 0.2 });
          }}
          minZoom={0.25}
          maxZoom={1.6}
          onNodeClick={(_, node) => {
            if (node.id === 'root') onSelect('root');
            else onSelect(Number(node.id));
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={18} color="#e7e5e4" />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeStrokeWidth={2}
            maskColor="rgba(28, 25, 23, 0.06)"
            nodeColor={(node) => {
              const data = node.data as CanvasNodeData;
              if (data.kind === 'intervention') return '#fcd34d';
              if (data.onPath) return '#2563eb';
              return '#d6d3d1';
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
