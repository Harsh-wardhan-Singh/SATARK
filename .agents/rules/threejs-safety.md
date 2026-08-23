---
trigger: glob
globs: frontend/src/city/**
---

# NEXUS Three.js Renderer Safety Rules

## SCOPE

These rules apply to the SATARK Three.js city-rendering subsystem.

Relevant path:

frontend/src/city/

They exist to protect the existing NEXUS renderer.

---

# 1. PROTECTED REFERENCE

The existing:

NEXUS_toon_city_v32.html

is the known-good reference implementation for the city renderer.

The objective is:

EXTRACT
→ INTEGRATE
→ EXTEND

NOT:

REWRITE
→ APPROXIMATE
→ REPLACE

---

# 2. ORIGINAL RENDERER MUST BE UNDERSTOOD FIRST

Before modifying renderer behavior:

1. inspect the original NEXUS renderer
2. identify the relevant implementation
3. understand its dependencies
4. identify the smallest required change
5. preserve unrelated behavior
6. implement
7. verify visual parity

Do not blindly rewrite unfamiliar Three.js code.

---

# 3. PRESERVE THE EXISTING CITY

Unless explicitly instructed otherwise, preserve:

- city.glb
- building geometry
- building materials
- facade treatment
- building facade texture
- terrain
- sea
- water animation
- road effects
- road-flow effects
- custom shaders
- lighting
- shadows
- fog
- camera
- camera framing
- post-processing
- GTAO
- bloom
- output processing
- resize behavior
- animation loop
- existing transforms
- FPS/performance monitoring

---

# 4. ASSET PATHS

The frontend city assets are:

frontend/public/city/

Expected runtime paths:

/city/city.glb
/city/building_facade.png
/city/sky_texture.jpg

Do not duplicate or regenerate these assets without explicit instruction.

If an asset fails to load:

1. inspect the request
2. inspect the path
3. inspect the server response
4. inspect the browser console
5. fix the actual issue

Do not hide a loading failure behind a placeholder.

---

# 5. DO NOT REPLACE THREE.JS

Do not replace native Three.js with:

- React Three Fiber
- another 3D engine
- a canvas abstraction
- a simplified renderer

unless explicitly instructed.

React surrounds the renderer.

React does not replace the renderer.

---

# 6. NEW SATARK VISUAL LAYERS

New visual systems should be layered over the existing city.

Examples:

- zone overlays
- zone labels
- safe-zone markers
- agent visualization
- evacuation visualization
- flood effects
- earthquake effects
- impact visualization

Do not modify unrelated city systems to implement these features.

---

# 7. CITY STATE ADAPTER

The CityStateAdapter is the boundary between application state and rendering state.

Conceptually:

Backend state
↓
Zustand
↓
CityStateAdapter
↓
Three.js representation

The adapter must not become a second simulation engine.

It translates authoritative state into visuals.

---

# 8. PERFORMANCE

Avoid:

- per-frame allocations
- repeated model loading
- repeated texture loading
- duplicated materials
- duplicated geometry
- unnecessary raycasts
- unnecessary render passes
- uncontrolled object creation
- unnecessary React synchronization

Reuse existing resources wherever appropriate.

---

# 9. RESOURCE LIFECYCLE

When dynamically creating Three.js resources, manage their lifecycle correctly.

Potential resources include:

- geometries
- materials
- textures
- render targets
- post-processing resources

Dispose resources when they are truly no longer required.

Do not dispose shared resources prematurely.

---

# 10. VISUAL PARITY

After renderer integration or significant modification, verify:

- city loads
- buildings appear correctly
- terrain appears correctly
- sea appears correctly
- roads appear correctly
- camera framing is preserved
- lighting is preserved
- shadows are preserved
- fog is preserved
- shaders work
- post-processing works
- GTAO works
- bloom works
- animations work
- resize works

Compare against the original renderer.

---

# 11. MAJOR CHANGE STOP CONDITION

If a requested feature appears to require a major rewrite of the protected renderer:

STOP before performing the rewrite.

Report:

- what must change
- why
- affected systems
- potential regression risks
- safer alternatives

Do not silently perform a major renderer rewrite.