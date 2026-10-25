import { useMemo, useState } from 'react';
import {
  Background,
  Controls,
  Handle,
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
  title: string;
  preview: string;
  kind: 'root' | 'persona' | 'intervention';
  onPath: boolean;
  hiddenCount: number;
  onContinue: () => void;
  onBranch: () => void;
  onHide: () => void;
};

function CanvasNode({ data, selected }: NodeProps<Node<CanvasNodeData>>) {
  const tone =
    data.kind === 'intervention'
      ? 'border-amber-300 bg-amber-50'
      : data.kind === 'root'
        ? 'border-stone-300 bg-stone-50'
        : 'border-stone-200 bg-white';
  const pathRing = data.onPath ? 'ring-2 ring-blue-400' : '';
  const selectedRing = selected ? 'ring-2 ring-stone-900' : '';

  return (
    <div className={`w-[210px] rounded-xl border px-3 py-2 text-left shadow-sm ${tone} ${pathRing} ${selectedRing}`}>
      <Handle type="target" position={Position.Top} className="!bg-stone-400" />
      <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">{data.title}</div>
      <p className="mt-1 line-clamp-3 text-xs leading-snug text-stone-800">{data.preview}</p>
      {data.hiddenCount > 0 && (
        <div className="mt-1 text-[11px] font-medium text-stone-500">{data.hiddenCount} hidden</div>
      )}
      <div className="mt-2 flex flex-wrap gap-1">
        <button
          type="button"
          className="rounded-md bg-stone-900 px-1.5 py-0.5 text-[10px] font-medium text-white"
          onClick={(event) => {
            event.stopPropagation();
            data.onContinue();
          }}
        >
          Continue
        </button>
        <button
          type="button"
          className="rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-900"
          onClick={(event) => {
            event.stopPropagation();
            data.onBranch();
          }}
        >
          Branch
        </button>
        <button
          type="button"
          className="rounded-md bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium text-stone-700"
          onClick={(event) => {
            event.stopPropagation();
            data.onHide();
          }}
        >
          {data.hiddenCount > 0 ? 'Show' : 'Hide'}
        </button>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-stone-400" />
    </div>
  );
}

const nodeTypes = { canvas: CanvasNode };

interface PlaygroundCanvasProps {
  goal: string;
  messages: SimulationMessage[];
  selectedId: NodeSelection;
  onSelect: (id: NodeSelection) => void;
  onContinue: (id: NodeSelection) => void;
  onBranch: (id: NodeSelection) => void;
}

function previewText(message: SimulationMessage): string {
  const text = (message.content || '').replace(/\s+/g, ' ').trim();
  return text.length > 140 ? `${text.slice(0, 137)}…` : text || '…';
}

export default function PlaygroundCanvas({
  goal,
  messages,
  selectedId,
  onSelect,
  onContinue,
  onBranch,
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
        positions.set(id, { x: slot * 250, y: depth * 170 });
        return slot;
      }
      const slots = kids.map((child) => place(child.id, depth + 1));
      const mid = (slots[0] + slots[slots.length - 1]) / 2;
      positions.set(id, { x: mid * 250, y: depth * 170 });
      return mid;
    };
    place('root', 0);

    const builtNodes: Node<CanvasNodeData>[] = [];
    const builtEdges: Edge[] = [];

    const rootPos = positions.get('root') ?? { x: 0, y: 0 };
    const rootHidden = descendantCount('root', children);
    builtNodes.push({
      id: 'root',
      type: 'canvas',
      position: rootPos,
      selected: selectedId === 'root',
      data: {
        title: 'Goal',
        preview: goal || 'Simulation goal',
        kind: 'root',
        onPath: pathIds.has('root'),
        hiddenCount: collapsed.has('root') ? rootHidden : 0,
        onContinue: () => onContinue('root'),
        onBranch: () => onBranch('root'),
        onHide: () => {
          setCollapsed((prev) => {
            const next = new Set(prev);
            if (next.has('root')) next.delete('root');
            else next.add('root');
            return next;
          });
        },
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
      const hiddenKids = collapsed.has(String(message.id)) ? descendantCount(message.id, children) : 0;
      builtNodes.push({
        id: String(message.id),
        type: 'canvas',
        position,
        selected: selectedId === message.id,
        data: {
          title: human ? `Facilitator · turn ${message.turn_number}` : `${message.persona_name} · turn ${message.turn_number}`,
          preview: previewText(message),
          kind: human ? 'intervention' : 'persona',
          onPath: pathIds.has(message.id),
          hiddenCount: hiddenKids,
          onContinue: () => onContinue(message.id),
          onBranch: () => onBranch(message.id),
          onHide: () => {
            setCollapsed((prev) => {
              const next = new Set(prev);
              const key = String(message.id);
              if (next.has(key)) next.delete(key);
              else next.add(key);
              return next;
            });
          },
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
  }, [collapsed, goal, messages, onBranch, onContinue, selectedId]);

  return (
    <div className="h-[520px] overflow-hidden rounded-2xl border border-stone-200 bg-[#f8f7f4]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onInit={(instance) => {
          void instance.fitView();
        }}
        minZoom={0.3}
        maxZoom={1.6}
        onNodeClick={(_, node) => {
          if (node.id === 'root') onSelect('root');
          else onSelect(Number(node.id));
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={18} color="#e7e5e4" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
