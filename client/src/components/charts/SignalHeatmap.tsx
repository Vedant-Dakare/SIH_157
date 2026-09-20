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
const HEADER_HEIGHT = 140;

const SEVERITY_FILL: Record<string, string> = {
  CRITICAL: '#123D73',
  HIGH: '#2F6FA3',
  MEDIUM: '#5B9BC4',
  LOW: '#9CCBE3',
  INFO: '#D9EAF4',
};

const SEVERITY_TEXT: Record<string, string> = {
  CRITICAL: '#ffffff',
  HIGH: '#ffffff',
  MEDIUM: '#ffffff',
  LOW: '#123D73',
  INFO: '#36566B',
};

/** Entity × signal grid as plain SVG. Click a fired cell to open the finding. */
export function SignalHeatmap({
  entities,
  signals,
  findings,
}: SignalHeatmapProps) {
  const navigate = useNavigate();

  const byCell = React.useMemo(() => {
    const map = new Map<string, Finding>();

    for (const finding of findings) {
      map.set(
        `${finding.entity_id}|${finding.signal_id}`,
        finding,
      );
    }

    return map;
  }, [findings]);

  const geometry = React.useMemo(() => {
    const width =
      ROW_LABEL_WIDTH +
      signals.length * (CELL + GAP) +
      GAP;

    const height =
      HEADER_HEIGHT +
      entities.length * (CELL + GAP) +
      GAP;

    return { width, height };
  }, [entities.length, signals.length]);

  if (entities.length === 0 || signals.length === 0) {
    return (
      <EmptyState
        title="No heatmap data"
        description="No entities or signals in this run."
      />
    );
  }

  const { width, height } = geometry;

  return (
    <div
      className="overflow-x-auto rounded-md border border-slate-200 bg-white p-3"
      aria-label="Signal heatmap"
    >
      <div
        className="flex"
        style={{ minWidth: Math.max(width, 600) }}
      >
        {/* Entity labels */}
        <div
          style={{ width: ROW_LABEL_WIDTH }}
          className="shrink-0 pt-1"
          aria-hidden="true"
        >
          <div
            style={{ height: HEADER_HEIGHT }}
            className="flex items-end pb-3"
          >
            <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
              Entity / CSE
            </span>
          </div>

          {entities.map((entity) => (
            <div
              key={entity.entity_id}
              style={{
                height: CELL,
                marginBottom: GAP,
              }}
              className="flex items-center gap-2 overflow-hidden pr-3"
            >
              <span
                className="truncate font-mono text-xs font-medium text-slate-700"
                title={entity.entity_id}
              >
                {entity.entity_id}
              </span>

              <RiskBadge
                band={entity.band}
                size="sm"
              />
            </div>
          ))}
        </div>

        {/* Heatmap */}
        <svg
          role="img"
          aria-label={`Heatmap of ${entities.length} entities by ${signals.length} signals`}
          width={width - ROW_LABEL_WIDTH}
          height={height}
          overflow="visible"
          className="shrink-0"
        >
          {/* Signal labels */}
{signals.map((signal, column) => {
  const x =
    column * (CELL + GAP) +
    GAP +
    CELL / 2-4;

  const y = 98;

  return (
    <g
      key={signal}
      transform={`translate(${x}, ${y}) rotate(-45)`}
    >
      <text
        x={0}
        y={0}
        fill="#475569"
        fontSize={10}
        fontWeight={600}
        textAnchor="end"
        dominantBaseline="middle"
      >
        {signal}
      </text>
    </g>
  );
})}

          {/* Cells */}
          {entities.map((entity, row) =>
            signals.map((signal, column) => {
              const finding = byCell.get(
                `${entity.entity_id}|${signal}`,
              );

              const x =
                column * (CELL + GAP) + GAP;

              const y =
                HEADER_HEIGHT +
                row * (CELL + GAP) +
                GAP;

              if (!finding) {
                return (
                  <rect
                    key={`${entity.entity_id}|${signal}`}
                    x={x}
                    y={y}
                    width={CELL}
                    height={CELL}
                    fill="#F8FAFC"
                    stroke="#D9E2EC"
                    strokeWidth={1}
                    rx={4}
                  >
                    <title>
                      {`${signal} did not fire on ${entity.entity_id}`}
                    </title>
                  </rect>
                );
              }

              const fill =
                SEVERITY_FILL[finding.severity] ??
                '#5B9BC4';

              const textColor =
                SEVERITY_TEXT[finding.severity] ??
                '#ffffff';

              return (
                <g
                  key={`${entity.entity_id}|${signal}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${signal} fired on ${entity.entity_id}, ${finding.severity} severity. Open finding.`}
                  style={{ cursor: 'pointer' }}
                  onClick={() =>
                    navigate(
                      `/findings/${finding.finding_id}`,
                    )
                  }
                  onKeyDown={(event) => {
                    if (
                      event.key === 'Enter' ||
                      event.key === ' '
                    ) {
                      event.preventDefault();

                      navigate(
                        `/findings/${finding.finding_id}`,
                      );
                    }
                  }}
                >
                  <rect
                    x={x}
                    y={y}
                    width={CELL}
                    height={CELL}
                    fill={fill}
                    stroke="#ffffff"
                    strokeWidth={1}
                    rx={4}
                  />

                  {/* Small severity indicator */}
                  <text
                    x={x + CELL / 2}
                    y={y + CELL / 2 + 3}
                    fill={textColor}
                    fontSize={8}
                    fontWeight={700}
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    •
                  </text>

                  <title>
                    {`${signal} fired on ${entity.entity_id} — ${finding.severity} severity`}
                  </title>
                </g>
              );
            }),
          )}
        </svg>
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate-100 pt-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
          Signal severity
        </span>

        {Object.entries(SEVERITY_FILL).map(
          ([severity, color]) => (
            <div
              key={severity}
              className="flex items-center gap-1.5"
            >
              <span
                className="h-3 w-3 rounded-sm border border-slate-200"
                style={{
                  backgroundColor: color,
                }}
                aria-hidden="true"
              />

              <span className="text-xs font-medium text-slate-600">
                {severity}
              </span>
            </div>
          ),
        )}
      </div>
    </div>
  );
}