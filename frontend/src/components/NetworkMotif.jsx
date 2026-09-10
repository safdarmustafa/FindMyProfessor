import React from 'react';

/**
 * A quiet constellation-of-nodes motif — standing in for a research/citation
 * network — used as texture on the navy marketing surfaces (landing hero,
 * login side panel). A handful of nodes are picked out in brass to suggest
 * "matches" surfacing out of the wider graph.
 */
const NODES = [
  { id: 1, x: 80, y: 120 }, { id: 2, x: 160, y: 260 }, { id: 3, x: 60, y: 380 },
  { id: 4, x: 220, y: 90 }, { id: 5, x: 300, y: 200, hi: true }, { id: 6, x: 260, y: 340 },
  { id: 7, x: 380, y: 120 }, { id: 8, x: 420, y: 260 }, { id: 9, x: 360, y: 420 },
  { id: 10, x: 500, y: 60 }, { id: 11, x: 540, y: 190, hi: true }, { id: 12, x: 600, y: 320 },
  { id: 13, x: 480, y: 380 }, { id: 14, x: 660, y: 140 }, { id: 15, x: 700, y: 280, hi: true },
  { id: 16, x: 640, y: 440 }, { id: 17, x: 180, y: 470 }, { id: 18, x: 760, y: 380 },
];

const EDGES = [
  [1, 2], [2, 3], [2, 5], [1, 4], [4, 5], [4, 7], [5, 6], [5, 8], [6, 9], [7, 8],
  [7, 10], [8, 9], [8, 11], [9, 13], [10, 11], [11, 12], [11, 14], [12, 13],
  [12, 15], [13, 16], [14, 15], [15, 18], [15, 16], [16, 13], [3, 17], [6, 17], [9, 17],
];

const byId = Object.fromEntries(NODES.map(n => [n.id, n]));

export default function NetworkMotif({ style, opacity = 1 }) {
  return (
    <svg
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid slice"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity, ...style }}
      aria-hidden="true"
    >
      <g stroke="rgba(201,164,99,.22)" strokeWidth="1">
        {EDGES.map(([a, b], i) => (
          <line key={i} x1={byId[a].x} y1={byId[a].y} x2={byId[b].x} y2={byId[b].y} />
        ))}
      </g>
      <g>
        {NODES.map(n => (
          <circle
            key={n.id}
            cx={n.x}
            cy={n.y}
            r={n.hi ? 5 : 2.6}
            fill={n.hi ? 'var(--brass)' : 'rgba(255,255,255,.35)'}
          />
        ))}
      </g>
    </svg>
  );
}
