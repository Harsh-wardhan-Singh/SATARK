---
description: Verify that the protected NEXUS Three.js city renderer remains visually and functionally intact after frontend changes.
---

# NEXUS Renderer Safety Check

Use this workflow whenever the existing Three.js city renderer is integrated, modified, or extended.

The objective is to ensure that SATARK frontend development does not break the known-good NEXUS city rendering.

---

## 1. Protected Reference

The original:

NEXUS_toon_city_v32.html

is the known-good visual and behavioral reference.

The frontend integration must preserve its important rendering behavior.

The objective is:

EXTRACT
→ INTEGRATE
→ EXTEND

not:

REWRITE
→ APPROXIMATE
→ REPLACE

---

## 2. Asset Verification

Verify that the following assets load successfully:

/city/city.glb

/city/building_facade.png

/city/sky_texture.jpg

Check the browser network panel for failed requests.

There must not be unexpected 404s or asset-loading errors.

---

## 3. City Geometry Verification

Verify that:

- the city model appears
- buildings appear
- terrain appears
- sea appears
- roads appear
- existing object placement is preserved
- the overall city composition remains consistent with the original renderer

---

## 4. Building Rendering Verification

Verify:

- building geometry
- building materials
- facade appearance
- facade texture
- existing building visual treatment

Do not accept a simplified placeholder rendering as equivalent to the original renderer.

---

## 5. Environment Verification

Verify:

- terrain
- sea
- water effects
- sky/environment
- fog
- existing atmospheric effects

---

## 6. Lighting Verification

Verify:

- scene lighting
- building lighting
- shadows
- existing light behavior
- overall visual balance

Do not silently replace the existing lighting system.

---

## 7. Road Verification

Verify:

- road geometry
- road appearance
- existing road-flow effects
- existing road animation

---

## 8. Shader Verification

Verify that existing custom shader systems still function.

Do not replace custom shaders with generic materials merely to simplify integration.

---

## 9. Post-Processing Verification

Verify:

- GTAO
- bloom
- output processing
- other existing post-processing passes

The final image should remain visually consistent with the original NEXUS renderer.

---

## 10. Camera Verification

Verify:

- initial camera position
- initial framing
- camera controls
- zoom/orbit behavior where applicable
- resize behavior
- viewport resizing

The city should not become incorrectly framed after frontend integration.

---

## 11. Animation Verification

Verify:

- main animation loop
- water animation
- road animation
- existing animated effects
- other existing continuous animations

Check that animations do not stop after React state changes.

---

## 12. SATARK Overlay Verification

If SATARK-specific visual layers have been added, verify that:

- zone overlays do not destroy the city rendering
- zone labels do not excessively obscure the city
- safe-zone markers render correctly
- agent visualization renders correctly
- evacuation visualization renders correctly
- flood effects render correctly
- earthquake effects render correctly
- impact visualization renders correctly

New layers must remain separate from unrelated original rendering systems.

---

## 13. React / Three.js Boundary Verification

Verify that:

- React is not recreating the entire city on ordinary state changes
- the Three.js scene is not stored wholesale in React state
- Three.js objects are not unnecessarily recreated
- the renderer maintains its own lifecycle
- the animation loop remains stable

---

## 14. Performance Verification

Look for obvious regressions:

- severe FPS reduction
- repeated GLTF loading
- repeated texture loading
- excessive object creation
- excessive render passes
- unnecessary per-frame allocations
- runaway animation loops
- excessive console errors

Do not optimize based purely on speculation, but do investigate obvious regressions.

---

## 15. Browser Console Verification

Check for:

- JavaScript errors
- Three.js errors
- shader errors
- asset errors
- WebGL errors
- repeated warnings

Resolve renderer errors before considering the renderer safe.

---

## 16. Final Assessment

If the original renderer remains visually and functionally intact:

RENDERER SAFE

If a meaningful regression is detected:

RENDERER REGRESSION DETECTED

When a regression is detected:

1. identify the affected subsystem
2. identify the likely cause
3. determine whether the new change caused it
4. fix it if the fix is safe and within scope
5. rerun the relevant checks

If fixing the regression would require a major rewrite of the protected renderer:

STOP.

Report:

- what would need to change
- why
- affected systems
- regression risk
- safer alternatives

Do not silently perform a major renderer rewrite.