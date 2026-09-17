import * as React from 'react';
import { useNavigate } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { RiskBadge } from '@/components/common/RiskBadge';
import type { Entity, Finding } from '@/types/api';

export interface SignalHeatmapProps {
  entities: Entity[];
  signals: string[];
  findings: Finding[];
}

const CELL = 28;
const GAP = 3;
const ROW_LABEL_WIDTH = 220;
const HEADER_HEIGHT = 110;

const SEVERITY_FILL: Record<string, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ef4444',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
  INFO: '#64748b',
};

/** Entity × signal grid as plain SVG. Click a fired cell to open the finding. */
export function SignalHeatmap({ entities, signals, findings }: SignalHeatmapProps) {
  const navigate = useNavigate();
  const byCell = React.useMemo(() => {
    const map = new Map<string, Finding>();
    for (const finding of findings) {
      map.set(`${finding.entity_id}|${finding.signal_id}`, finding);
    }
    return map;
  }, [findings]);
  const geometry = React.useMemo(() => {
    const width = ROW_LABEL_WIDTH + signals.length * (CELL + GAP) + GAP;
    const height = HEADER_HEIGHT + entities.length * (CELL + GAP) + GAP;
    return { width, height };
  }, [entities.length, signals.length]);
  if (entities.length === 0 || signals.length === 0) {
    return (
      <EmptyState title="No heatmap data" description="No entities or signals in this run." />
    );
  }
  const { width, height } = geometry;

  return (
    <div className="overflow-x-auto" aria-label="Signal heatmap">
      <div className="flex" style={{ minWidth: Math.max(width, 600) }}>
        <div style={{ width: ROW_LABEL_WIDTH }} className="shrink-0 pt-1" aria-hidden="true">
          <div style={{ height: HEADER_HEIGHT }} />
          {entities.map((entity) => (
            <div
              key={entity.entity_id}
              style={{ height: CELL, marginBottom: GAP }}
              className="flex items-center gap-2 overflow-hidden pr-2 text-xs text-slate-50"
            >
              <span className="truncate font-mono">{entity.entity_id}</span>
              <RiskBadge band={entity.band} size="sm" />
            </div>
          ))}
        </div>
        <svg
          role="img"
          aria-label={`Heatmap of ${entities.length} entities by ${signals.length} signals`}
          width={width - ROW_LABEL_WIDTH}
          height={height}
        >
          {signals.map((signal, column) => (
            <text
              key={signal}
              x={column * (CELL + GAP) + GAP + CELL / 2}
              y={HEADER_HEIGHT - 8}
              fill="#94a3b8"
              fontSize={10}
              textAnchor="end"
              transform={`rotate(-45 ${column * (CELL + GAP) + GAP + CELL / 2} ${HEADER_HEIGHT - 8})`}
            >
              {signal}
            </text>
          ))}
          {entities.map((entity, row) =>
            signals.map((signal, column) => {
              const finding = byCell.get(`${entity.entity_id}|${signal}`);
              const x = column * (CELL + GAP) + GAP;
              const y = HEADER_HEIGHT + row * (CELL + GAP) + GAP;
              if (!finding) {
                return (
                  <rect
                    key={`${entity.entity_id}|${signal}`}
                    x={x}
                    y={y}
                    width={CELL}
                    height={CELL}
                    fill="transparent"
                    stroke="#1e293b"
                    strokeWidth={1}
                    rx={4}
                  >
                    <title>{`${signal} did not fire on ${entity.entity_id}`}</title>
                  </rect>
                );
              }
              return (
                <rect
                  key={`${entity.entity_id}|${signal}`}
                  x={x}
                  y={y}
                  width={CELL}
                  height={CELL}
                  fill={SEVERITY_FILL[finding.severity] ?? '#64748b'}
                  rx={4}
                  role="button"
                  tabIndex={0}
                  aria-label={`${signal} fired on ${entity.entity_id}, ${finding.severity} severity. Open finding.`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/findings/${finding.finding_id}`)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      navigate(`/findings/${finding.finding_id}`);
                    }
                  }}
                >
                  <title>{`${signal} fired on ${entity.entity_id} — ${finding.severity} severity`}</title>
                </rect>
              );
            }),
          )}
        </svg>
      </div>
    </div>
  );
}
