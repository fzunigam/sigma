import { useMemo, useRef, useState, type PointerEvent } from 'react';
import { money, shortDate } from '../lib/format';
import type { ValuePoint } from '../lib/types';

interface Props {
  points: ValuePoint[];
}

const WIDTH = 640;
const HEIGHT = 160;
const PAD_X = 8;
const PAD_TOP = 16;
const PAD_BOTTOM = 24;

/**
 * A single-series line: the portfolio's value over time. One color (the
 * accent), no legend — a single line needs none — and a crosshair tooltip
 * since every value it shows is also readable from the positions table
 * above it. Straight segments, not a smoothed curve: the data is one point
 * per day, so a curve would imply precision between points that isn't there.
 */
export function PortafolioChart({ points }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const scale = useMemo(() => buildScale(points), [points]);

  if (points.length < 2) {
    return (
      <p className="text-xs text-text-subtle py-8 text-center">
        El gráfico aparece a medida que uses Inversiones: se guarda un punto cada vez
        que se actualizan los precios.
      </p>
    );
  }

  const coords = points.map((point, index) => ({
    x: scale.x(index),
    y: scale.y(point.value_clp),
  }));
  const linePath = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x},${c.y}`).join(' ');
  const areaPath = `${linePath} L${coords[coords.length - 1].x},${HEIGHT - PAD_BOTTOM} L${coords[0].x},${HEIGHT - PAD_BOTTOM} Z`;
  const last = points[points.length - 1];

  function onMove(event: PointerEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const relativeX = ((event.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let nearestDistance = Infinity;
    coords.forEach((c, index) => {
      const distance = Math.abs(c.x - relativeX);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearest = index;
      }
    });
    setHoverIndex(nearest);
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null;
  const hoveredCoord = hoverIndex !== null ? coords[hoverIndex] : null;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full h-40"
        onPointerMove={onMove}
        onPointerLeave={() => setHoverIndex(null)}
        role="img"
        aria-label={`Valor de la cartera en el tiempo, hoy ${money(last.value_clp)}`}
      >
        {scale.ticks.map((tick) => (
          <line
            key={tick.value}
            x1={PAD_X}
            x2={WIDTH - PAD_X}
            y1={scale.y(tick.value)}
            y2={scale.y(tick.value)}
            className="stroke-line"
            strokeWidth={1}
          />
        ))}

        <path d={areaPath} fill="var(--accent)" opacity={0.1} stroke="none" />
        <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        <circle
          cx={coords[coords.length - 1].x}
          cy={coords[coords.length - 1].y}
          r={4}
          fill="var(--accent)"
          stroke="var(--surface)"
          strokeWidth={2}
        />

        {hoveredCoord && (
          <>
            <line
              x1={hoveredCoord.x}
              x2={hoveredCoord.x}
              y1={PAD_TOP}
              y2={HEIGHT - PAD_BOTTOM}
              className="stroke-line-strong"
              strokeWidth={1}
            />
            <circle
              cx={hoveredCoord.x}
              cy={hoveredCoord.y}
              r={4}
              fill="var(--accent)"
              stroke="var(--surface)"
              strokeWidth={2}
            />
          </>
        )}
      </svg>

      <p className="absolute right-1 top-0 text-[11px] text-text-subtle tnum">
        {money(last.value_clp)}
      </p>

      {hovered && hoveredCoord && (
        <div
          className="pointer-events-none absolute -translate-x-1/2 -translate-y-full
            bg-surface border border-line-strong rounded-[6px] px-2 py-1.5 text-[11px]
            shadow-[var(--shadow-float)] whitespace-nowrap"
          style={{
            left: `${(hoveredCoord.x / WIDTH) * 100}%`,
            top: `${(hoveredCoord.y / HEIGHT) * 100}%`,
          }}
        >
          <p className="font-medium tnum">{money(hovered.value_clp)}</p>
          <p className="text-text-subtle">{shortDate(hovered.date)}</p>
        </div>
      )}
    </div>
  );
}

function buildScale(points: ValuePoint[]) {
  const values = points.map((p) => p.value_clp);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const span = max - min || 1;
  const innerWidth = WIDTH - PAD_X * 2;
  const innerHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;

  const x = (index: number) =>
    points.length <= 1 ? PAD_X : PAD_X + (index / (points.length - 1)) * innerWidth;
  const y = (value: number) => PAD_TOP + innerHeight - ((value - min) / span) * innerHeight;

  const ticks = [min, min + span / 2, max].map((value) => ({ value }));
  return { x, y, ticks };
}
