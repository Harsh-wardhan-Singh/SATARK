---
description: Safely implement one major SATARK frontend development phase with planning, implementation, verification, browser testing, and regression checks.
---

# SATARK Frontend Phase

Follow this procedure whenever implementing a major SATARK frontend development phase.

## 1. Understand Before Coding

Before changing anything:

- Read the applicable SATARK Rules.
- Read the relevant Skills.
- Inspect the existing implementation.
- Inspect relevant types.
- Inspect relevant API contracts.
- Inspect the existing NEXUS renderer if the phase affects the 3D city.
- Inspect the current Git status.

Do not begin implementation until the relevant existing code has been understood.

Do not assume that an unfamiliar change is incorrect or belongs to you. Another developer may be working in the repository.

---

## 2. Establish the Implementation Boundary

Before coding, determine:

- Which files need to be created?
- Which files need to be modified?
- Which files must not be touched?
- Does the feature require a backend contract?
- Does the feature affect Three.js?
- Does the feature affect shared types?
- Does the feature affect another developer's subsystem?

The normal frontend implementation boundary is:

frontend/**

Do not modify backend/** unless explicitly required and coordinated.

Do not modify unrelated shared files.

---

## 3. Produce an Implementation Plan

Create a concise plan containing:

- objective
- user-facing behavior
- files to create
- files to modify
- state changes
- API requirements
- renderer requirements
- dependencies
- verification strategy

The plan must respect the existing SATARK architecture.

Do not invent backend behavior.

Do not introduce speculative features.

---

## 4. Inspect Before Modifying

For every existing file that will be modified:

- read the relevant implementation
- understand its current responsibility
- identify dependencies
- identify existing patterns
- preserve unrelated behavior

For renderer work, inspect the original NEXUS renderer and preserve its behavior.

Do not replace working systems merely because another implementation appears cleaner.

---

## 5. Implement

Implement the smallest complete solution that satisfies the phase requirements.

Follow:

- SATARK Core Rules
- Frontend Architecture Rules
- NEXUS renderer safety rules when applicable
- relevant Skills

Do not perform unrelated refactoring.

Do not rewrite existing systems unnecessarily.

Do not fabricate API contracts.

Do not create fake functionality and present it as real backend behavior.

If a required backend contract is unavailable, isolate any mock data clearly and report the missing contract.

---

## 6. Static Verification

After implementation, run the project's available verification commands.

At minimum, where configured:

- TypeScript validation
- lint
- production build

Fix errors introduced by the implementation.

Do not suppress errors merely to obtain a successful build.

---

## 7. Runtime Verification

Run the frontend application.

Check:

- application startup
- browser console
- runtime errors
- failed network requests
- missing assets
- failed API requests
- unexpected warnings

If the feature interacts with the city, verify that the city still loads correctly.

---

## 8. Browser Verification

Actually open and use the application.

Do not consider successful compilation sufficient.

Exercise the feature as a real operator would.

Verify:

- normal behavior
- loading behavior
- error behavior
- empty states where applicable
- interactions
- navigation
- visual layout
- responsive behavior

For simulation functionality, verify the actual operator flow rather than merely checking that buttons render.

---

## 9. Renderer Verification

If any file under:

frontend/src/city/**

was modified, perform the NEXUS renderer safety verification.

Verify that:

- city.glb loads
- building facade texture loads
- sky texture loads
- city geometry remains intact
- camera behavior remains intact
- lighting remains intact
- shadows remain intact
- fog remains intact
- shaders remain intact
- water remains intact
- roads remain intact
- GTAO remains intact
- bloom remains intact
- existing animations remain intact

Any renderer regression must be investigated before the phase is considered complete.

---

## 10. Regression Check

Check that existing functionality still works.

Pay particular attention to:

- existing navigation
- existing Digital Twin functionality
- existing city rendering
- asset loading
- simulation controls already implemented
- existing state management

Do not assume that a successful build means there are no regressions.

---

## 11. Collaboration Check

Before completion:

- inspect Git status
- identify files modified by this task
- ensure unrelated changes were not overwritten
- ensure backend/** was not modified unnecessarily
- ensure another developer's work was preserved

Do not use destructive Git commands to clean up unexpected changes.

Never use commands such as:

- git reset --hard
- git clean -fd
- git restore .
- git checkout -- .

to discard work unless explicitly instructed.

---

## 12. Final Verification

Repeat the relevant verification after fixing any discovered issues.

Do not stop after fixing an issue without rerunning the affected verification.

---

## 13. Final Report

When complete, report:

### Implemented

Describe exactly what was implemented.

### Files Changed

List files created and modified.

### Verification Performed

List:

- typecheck
- lint
- build
- browser verification
- console verification
- network verification
- renderer verification where applicable

### Problems Found and Fixed

List meaningful issues discovered during verification.

### Remaining Limitations

Clearly state anything that could not be verified or requires backend work.

Never claim that an unverified behavior works.