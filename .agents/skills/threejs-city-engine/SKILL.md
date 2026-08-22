---
name: threejs-city-engine
description: Use when modifying or integrating SATARK's Three.js city renderer under frontend/src/city/, including city.glb loading, shaders, materials, post-processing, zone overlays, safe zones, agents, calamity effects, and renderer performance.
---

# NEXUS City Engine Skill

## Purpose

Safely integrate and extend the existing NEXUS Three.js city renderer.

The renderer is protected infrastructure.

---

## Reference

The original:

NEXUS_toon_city_v32.html

is the behavioral and visual reference.

Do not replace it casually.

---

## Strategy

Use:

EXTRACT
→ INTEGRATE
→ EXTEND

Do not:

REWRITE
→ APPROXIMATE

---

## Preserve

Preserve the existing:

- city model
- materials
- facade treatment
- terrain
- sea
- roads
- shaders
- lighting
- shadows
- fog
- camera
- GTAO
- bloom
- post-processing
- animation
- resize behavior

---

## SATARK Layers

New layers include:

- zones
- safe zones
- agents
- evacuation
- flood
- earthquake
- impact visualization

These should be layered over the existing city.

---

## State Boundary

Use:

backend
→ API
→ Zustand
→ CityStateAdapter
→ Three.js

Do not put backend simulation logic into the renderer.

---

## Performance

Prefer:

- reuse
- caching
- stable objects
- batching
- instancing when genuinely useful

Avoid:

- per-frame allocations
- repeated loading
- duplicate resources
- unnecessary render passes

---

## Verification

After renderer changes:

- run the application
- open the Digital Twin
- verify assets
- verify visuals
- verify animations
- verify camera
- verify console
- verify network
- check for obvious performance regressions

The renderer must remain visually recognizable as the original NEXUS city.