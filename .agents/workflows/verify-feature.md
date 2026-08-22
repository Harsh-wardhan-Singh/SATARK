---
description: Perform a rigorous verification pass on a SATARK frontend feature before it is considered complete.
---

# Verify SATARK Feature

Use this workflow whenever a SATARK frontend feature needs a final quality and regression check.

The objective is to verify the actual application, not merely the source code.

---

## 1. Inspect the Changes

Review the changes made for the current feature.

Identify:

- changed files
- newly created files
- modified dependencies
- state changes
- API changes
- renderer changes
- unrelated modifications
- potential architectural violations

If unrelated files were modified, investigate why before continuing.

---

## 2. Verify Architecture

Confirm that:

- React remains responsible for UI
- Three.js remains responsible for 3D rendering
- backend communication remains in the API layer
- Zustand remains responsible for intended application state
- backend logic has not been duplicated in the frontend
- zone-based interaction is preserved
- building-level inspection has not been introduced
- no vehicle subsystem has been introduced
- only Flood and Earthquake are supported
- safe zones remain backend-authoritative

---

## 3. TypeScript Verification

Run the project's TypeScript validation.

Check for:

- type errors
- unsafe casts
- unnecessary any
- missing types
- incorrect API assumptions
- duplicated domain types

Fix newly introduced issues.

---

## 4. Lint Verification

Run the configured lint command.

Fix newly introduced lint errors.

Do not disable lint rules merely to hide an implementation problem.

---

## 5. Production Build

Run the production build.

Verify that:

- compilation succeeds
- assets are correctly referenced
- no build errors are present

Investigate warnings when they indicate a real issue.

---

## 6. Start the Application

Start the frontend using the project's normal development command.

Confirm that the application starts successfully.

---

## 7. Browser Verification

Open the relevant application page.

Actually interact with the implemented feature.

Verify:

- controls
- navigation
- state changes
- loading behavior
- error behavior
- success behavior
- empty states where applicable
- responsive behavior

Do not rely solely on source inspection.

---

## 8. Console Verification

Inspect the browser console.

Look for:

- JavaScript errors
- React errors
- Three.js errors
- failed asset loading
- repeated warnings
- unexpected exceptions

Resolve errors introduced by the feature.

---

## 9. Network Verification

Inspect network activity.

Look for:

- 404 errors
- failed API requests
- incorrect asset paths
- duplicate requests
- repeated model loading
- unexpected requests

Do not hide a failed request with a fake UI state.

---

## 10. Visual Verification

Check the actual interface.

Verify:

- layout
- spacing
- hierarchy
- readability
- status indicators
- buttons
- panels
- overlays
- responsive behavior
- 3D viewport

The city should remain the visual focus where appropriate.

---

## 11. Three.js Verification

If the feature touches the city renderer, verify:

- city.glb loads
- textures load
- camera works
- buildings remain correct
- terrain remains correct
- sea remains correct
- roads remain correct
- lighting remains correct
- shadows remain correct
- fog remains correct
- shaders remain correct
- GTAO remains correct
- bloom remains correct
- existing animations remain correct

---

## 12. Performance Check

Look for obvious regressions:

- severe FPS degradation
- repeated GLTF loading
- repeated texture loading
- excessive object creation
- per-frame allocations
- unnecessary rerenders
- unnecessary post-processing
- runaway animation loops

Do not optimize unrelated code without evidence.

---

## 13. Regression Check

Verify nearby existing functionality.

A feature is not successful if it works while breaking existing functionality.

---

## 14. Final Result

Return one of:

PASS

or

FAIL

If FAIL:

1. list each failure
2. identify the likely cause
3. fix the failure where appropriate
4. rerun the affected verification
5. only return PASS after the issue is actually resolved

Never hide unresolved failures.

Never report PASS merely because the application builds.