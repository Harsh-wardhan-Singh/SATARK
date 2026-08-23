/**
 * Bounded Voronoi partition for SATARK zone boundary visualization.
 *
 * DERIVED VISUALIZATION ONLY — the authoritative zone membership rule
 * remains nearest-center (see spatial.ts).
 *
 * Algorithm: half-plane clipping (Sutherland-Hodgman style).
 * For each zone center Pi, start with the full map rectangle and
 * iteratively clip by the perpendicular bisector of Pi–Pj for every
 * other center Pj.  The result is the bounded Voronoi cell for Pi.
 *
 * Suitable for exactly 21 points — correctness over micro-optimization.
 */

// ────────────────────────────────────────────────────────────
// Public types
// ────────────────────────────────────────────────────────────

export interface Point2D {
  x: number;
  z: number;
}

export interface WorldBounds {
  xMin: number;
  xMax: number;
  zMin: number;
  zMax: number;
}

export interface VoronoiCell {
  zoneId: string;
  vertices: Point2D[];
}

// ────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────

/** Numerical epsilon for parallel-line detection. */
const EPS = 1e-9;

// ────────────────────────────────────────────────────────────
// Internal helpers
// ────────────────────────────────────────────────────────────

/**
 * Clip a convex polygon to the half-plane defined by:
 *   nx * x + nz * z <= d
 *
 * Uses the Sutherland-Hodgman algorithm for a single edge.
 */
function clipPolygonByHalfPlane(
  polygon: Point2D[],
  nx: number,
  nz: number,
  d: number,
): Point2D[] {
  if (polygon.length === 0) return [];

  const output: Point2D[] = [];
  const n = polygon.length;

  for (let i = 0; i < n; i++) {
    const current = polygon[i];
    const next = polygon[(i + 1) % n];

    const dCurrent = nx * current.x + nz * current.z - d;
    const dNext = nx * next.x + nz * next.z - d;

    const currentInside = dCurrent <= EPS;
    const nextInside = dNext <= EPS;

    if (currentInside) {
      output.push(current);
    }

    // If the edge crosses the boundary, add the intersection point
    if ((currentInside && !nextInside) || (!currentInside && nextInside)) {
      const denom = dCurrent - dNext;
      if (Math.abs(denom) > EPS) {
        const t = dCurrent / denom;
        output.push({
          x: current.x + t * (next.x - current.x),
          z: current.z + t * (next.z - current.z),
        });
      }
    }
  }

  return output;
}

/**
 * Build the bounding rectangle polygon (CCW winding) from world bounds.
 */
function boundsToPolygon(bounds: WorldBounds): Point2D[] {
  return [
    { x: bounds.xMin, z: bounds.zMin },
    { x: bounds.xMax, z: bounds.zMin },
    { x: bounds.xMax, z: bounds.zMax },
    { x: bounds.xMin, z: bounds.zMax },
  ];
}

// ────────────────────────────────────────────────────────────
// Public API
// ────────────────────────────────────────────────────────────

/**
 * Compute bounded Voronoi cells for a set of zone centers.
 *
 * @param centers – Array of `{ id, center: {x, z} }` — the 21 authoritative zone centers.
 * @param bounds  – The authoritative world bounds from `glb_zone_mapping.json`.
 * @returns A Map from zone ID to its derived VoronoiCell.
 * @throws If any center produces an empty or degenerate cell.
 */
export function computeVoronoiCells(
  centers: { id: string; center: Point2D }[],
  bounds: WorldBounds,
): Map<string, VoronoiCell> {
  // ── Validate inputs ──
  if (centers.length === 0) {
    throw new Error('computeVoronoiCells: no centers provided');
  }

  const seenIds = new Set<string>();
  for (const c of centers) {
    if (seenIds.has(c.id)) {
      throw new Error(`computeVoronoiCells: duplicate center ID "${c.id}"`);
    }
    seenIds.add(c.id);
    if (!Number.isFinite(c.center.x) || !Number.isFinite(c.center.z)) {
      throw new Error(`computeVoronoiCells: NaN/Infinite coordinate in center "${c.id}"`);
    }
  }

  if (bounds.xMin >= bounds.xMax || bounds.zMin >= bounds.zMax) {
    throw new Error(`computeVoronoiCells: invalid bounds (min >= max)`);
  }

  // ── Build cells ──
  const result = new Map<string, VoronoiCell>();
  const boundsPoly = boundsToPolygon(bounds);

  for (let i = 0; i < centers.length; i++) {
    const pi = centers[i];
    let cell = [...boundsPoly]; // start with the full rectangle

    for (let j = 0; j < centers.length; j++) {
      if (i === j) continue;
      const pj = centers[j];

      // Perpendicular bisector of Pi–Pj:
      //   midpoint M = (Pi + Pj) / 2
      //   normal  N  = Pj − Pi  (pointing AWAY from Pi)
      //
      // The half-plane closer to Pi satisfies:
      //   N · (P − M) <= 0
      //   i.e. nx * (x − mx) + nz * (z − mz) <= 0
      //   i.e. nx * x + nz * z <= nx * mx + nz * mz
      const mx = (pi.center.x + pj.center.x) / 2;
      const mz = (pi.center.z + pj.center.z) / 2;
      const nx = pj.center.x - pi.center.x;
      const nz = pj.center.z - pi.center.z;
      const d = nx * mx + nz * mz;

      cell = clipPolygonByHalfPlane(cell, nx, nz, d);

      if (cell.length < 3) {
        // Early out — cell already degenerate
        break;
      }
    }

    // ── Validate cell ──
    if (cell.length < 3) {
      throw new Error(
        `computeVoronoiCells: degenerate cell for zone "${pi.id}" (${cell.length} vertices)`,
      );
    }

    for (const v of cell) {
      if (!Number.isFinite(v.x) || !Number.isFinite(v.z)) {
        throw new Error(
          `computeVoronoiCells: NaN vertex in cell for zone "${pi.id}"`,
        );
      }
    }

    result.set(pi.id, { zoneId: pi.id, vertices: cell });
  }

  return result;
}

/**
 * Convenience wrapper: compute cells from `Zone[]` and `WorldBounds`.
 *
 * The returned cells are DERIVED VISUALIZATION — they do NOT belong
 * in the authoritative domain model.
 */
export function getDerivedZoneCells(
  zones: { id: string; center_world: Point2D }[],
  bounds: WorldBounds,
): Map<string, VoronoiCell> {
  const centers = zones.map((z) => ({
    id: z.id,
    center: { x: z.center_world.x, z: z.center_world.z },
  }));
  return computeVoronoiCells(centers, bounds);
}

/**
 * Compute Voronoi cells clipped to an actual terrain footprint polygon.
 *
 * When a terrain footprint is provided, it replaces the bounding
 * rectangle as the starting polygon for each cell's half-plane
 * clipping.  The resulting cells are:
 *
 *     terrainFootprint ∩ VoronoiCell(Pi)
 *
 * This means the outer edges of the zone boundary network follow
 * the actual terrain boundary rather than the broad rectangular
 * world bounds.
 *
 * Falls back to rectangular bounds if no footprint is available.
 *
 * @param zones     – The 21 authoritative zone definitions.
 * @param bounds    – The rectangular world bounds (fallback).
 * @param footprint – The terrain boundary polygon in world X/Z,
 *                    or null to fall back to bounds rectangle.
 */
export function getDerivedZoneCellsWithFootprint(
  zones: { id: string; center_world: Point2D }[],
  bounds: WorldBounds,
  footprint: Point2D[] | null,
): Map<string, VoronoiCell> {
  if (!footprint || footprint.length < 3) {
    return getDerivedZoneCells(zones, bounds);
  }

  const centers = zones.map((z) => ({
    id: z.id,
    center: { x: z.center_world.x, z: z.center_world.z },
  }));

  return computeVoronoiCellsWithFootprint(centers, bounds, footprint);
}

/**
 * Core Voronoi computation using a terrain footprint as the
 * starting polygon instead of a bounding rectangle.
 */
function computeVoronoiCellsWithFootprint(
  centers: { id: string; center: Point2D }[],
  bounds: WorldBounds,
  footprint: Point2D[],
): Map<string, VoronoiCell> {
  // ── Validate inputs ──
  if (centers.length === 0) {
    throw new Error('computeVoronoiCellsWithFootprint: no centers provided');
  }

  const seenIds = new Set<string>();
  for (const c of centers) {
    if (seenIds.has(c.id)) {
      throw new Error(`computeVoronoiCellsWithFootprint: duplicate center ID "${c.id}"`);
    }
    seenIds.add(c.id);
    if (!Number.isFinite(c.center.x) || !Number.isFinite(c.center.z)) {
      throw new Error(`computeVoronoiCellsWithFootprint: NaN/Infinite coordinate in center "${c.id}"`);
    }
  }

  if (bounds.xMin >= bounds.xMax || bounds.zMin >= bounds.zMax) {
    throw new Error('computeVoronoiCellsWithFootprint: invalid bounds (min >= max)');
  }

  // ── Build cells ──
  const result = new Map<string, VoronoiCell>();

  for (let i = 0; i < centers.length; i++) {
    const pi = centers[i];
    // Start with the terrain footprint polygon instead of the rectangle
    let cell = [...footprint];

    for (let j = 0; j < centers.length; j++) {
      if (i === j) continue;
      const pj = centers[j];

      // Perpendicular bisector of Pi–Pj (same as computeVoronoiCells)
      const mx = (pi.center.x + pj.center.x) / 2;
      const mz = (pi.center.z + pj.center.z) / 2;
      const nx = pj.center.x - pi.center.x;
      const nz = pj.center.z - pi.center.z;
      const d = nx * mx + nz * mz;

      cell = clipPolygonByHalfPlane(cell, nx, nz, d);

      if (cell.length < 3) {
        break;
      }
    }

    // ── Validate cell ──
    if (cell.length < 3) {
      throw new Error(
        `computeVoronoiCellsWithFootprint: degenerate cell for zone "${pi.id}" (${cell.length} vertices)`,
      );
    }

    for (const v of cell) {
      if (!Number.isFinite(v.x) || !Number.isFinite(v.z)) {
        throw new Error(
          `computeVoronoiCellsWithFootprint: NaN vertex in cell for zone "${pi.id}"`,
        );
      }
    }

    result.set(pi.id, { zoneId: pi.id, vertices: cell });
  }

  return result;
}
