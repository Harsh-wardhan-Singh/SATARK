/**
 * Terrain footprint extraction from a loaded GLTF/GLB scene.
 *
 * Finds all meshes whose *original* material was named `MAT_TERRAIN`,
 * extracts their boundary edges (edges belonging to exactly one triangle),
 * chains them into a closed polygon loop, and returns that polygon
 * in world-space X/Z coordinates.
 *
 * The result represents the actual land/city footprint from the GLB.
 *
 * This is a one-shot computation called once after city.glb loads.
 */

import * as THREE from 'three';
import { Point2D } from '../zones/voronoi';

// ────────────────────────────────────────────────────────────
// Public API
// ────────────────────────────────────────────────────────────

/**
 * Extract the terrain boundary polygon from a loaded GLTF scene.
 *
 * @param terrainMeshes – Array of THREE.Mesh objects that had
 *   `MAT_TERRAIN` as their original material name. Caller is
 *   responsible for collecting these during the GLB traversal.
 * @returns The world-space X/Z boundary polygon, or null if
 *   no valid terrain geometry was found.
 */
export function extractTerrainFootprint(
  terrainMeshes: THREE.Mesh[],
): Point2D[] | null {
  if (terrainMeshes.length === 0) return null;

  // Collect all world-space vertices and triangle indices
  // across all terrain meshes (typically just one).
  const allVertices: THREE.Vector3[] = [];
  const allTriangles: [number, number, number][] = [];

  for (const mesh of terrainMeshes) {
    const geometry = mesh.geometry;
    const position = geometry.attributes.position;
    if (!position) continue;

    // Ensure mesh world matrix is up to date
    mesh.updateWorldMatrix(true, false);

    const baseIndex = allVertices.length;
    const count = position.count;

    // Transform every vertex to world space
    const v = new THREE.Vector3();
    for (let i = 0; i < count; i++) {
      v.fromBufferAttribute(position as THREE.BufferAttribute, i);
      v.applyMatrix4(mesh.matrixWorld);
      allVertices.push(v.clone());
    }

    // Read index buffer (or generate sequential indices)
    const index = geometry.index;
    if (index) {
      for (let i = 0; i < index.count; i += 3) {
        allTriangles.push([
          baseIndex + index.getX(i),
          baseIndex + index.getX(i + 1),
          baseIndex + index.getX(i + 2),
        ]);
      }
    } else {
      // Non-indexed geometry: every 3 consecutive vertices form a triangle
      for (let i = 0; i < count; i += 3) {
        allTriangles.push([baseIndex + i, baseIndex + i + 1, baseIndex + i + 2]);
      }
    }
  }

  if (allVertices.length < 3 || allTriangles.length === 0) return null;

  // ── Find boundary edges ──
  // A boundary edge belongs to exactly one triangle.
  // Use position-based keys (rounded) so that coincident vertices
  // from different meshes or index entries merge correctly.
  const edgeCount = new Map<string, number>();
  const PRECISION = 4; // decimal places

  const vertexKey = (v: THREE.Vector3): string =>
    `${v.x.toFixed(PRECISION)}_${v.z.toFixed(PRECISION)}`;

  const edgeKey = (ka: string, kb: string): string =>
    ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;

  for (const [ia, ib, ic] of allTriangles) {
    const ka = vertexKey(allVertices[ia]);
    const kb = vertexKey(allVertices[ib]);
    const kc = vertexKey(allVertices[ic]);

    const edges = [
      edgeKey(ka, kb),
      edgeKey(kb, kc),
      edgeKey(kc, ka),
    ];

    for (const ek of edges) {
      edgeCount.set(ek, (edgeCount.get(ek) || 0) + 1);
    }
  }

  // ── Collect boundary edges ──
  const boundaryAdj = new Map<string, string[]>();

  const addAdj = (a: string, b: string) => {
    let list = boundaryAdj.get(a);
    if (!list) {
      list = [];
      boundaryAdj.set(a, list);
    }
    list.push(b);
  };

  for (const [ek, cnt] of edgeCount) {
    if (cnt !== 1) continue;
    const [ka, kb] = ek.split('|');
    addAdj(ka, kb);
    addAdj(kb, ka);
  }

  if (boundaryAdj.size < 3) return null;

  // ── Trace the boundary loop ──
  // Start from an arbitrary boundary vertex and walk the loop.
  const visited = new Set<string>();
  const startKey = boundaryAdj.keys().next().value;
  if (!startKey) return null;

  const loop: Point2D[] = [];
  let current: string | undefined = startKey;

  while (current && !visited.has(current)) {
    visited.add(current);
    const [xStr, zStr] = current.split('_');
    loop.push({ x: parseFloat(xStr), z: parseFloat(zStr) });

    const neighbors = boundaryAdj.get(current);
    current = neighbors?.find((n) => !visited.has(n));
  }

  if (loop.length < 3) return null;

  return loop;
}
