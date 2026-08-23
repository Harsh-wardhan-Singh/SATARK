---
name: frontend-quality
description: Use when implementing, reviewing, or verifying SATARK frontend features. Performs TypeScript, React, build, browser, UI, runtime, performance, and regression quality checks.
---

# SATARK Frontend Quality Skill

## Principle

Code generation is not verification.

A feature is complete only after appropriate verification.

---

## Static Checks

Run the project's configured:

- TypeScript validation
- lint
- production build

Fix newly introduced errors.

Do not suppress errors merely to obtain a successful build.

---

## Runtime Checks

Run the application.

Check:

- browser console
- network requests
- runtime errors
- failed asset requests
- failed API requests

---

## Browser Checks

Actually interact with the feature.

Verify:

- layout
- controls
- navigation
- loading
- errors
- success behavior
- 3D viewport
- responsive behavior

---

## React Checks

Look for:

- stale closures
- incorrect hook dependencies
- unnecessary rerenders
- missing cleanup
- duplicated state
- giant components

---

## Three.js Checks

Look for:

- repeated object creation
- repeated model loading
- resource leaks
- unnecessary render work
- per-frame allocations
- incorrect disposal

---

## Regression Checks

Verify that existing functionality remains intact.

The NEXUS city renderer receives special protection.

---

## Final Report

Report:

- implemented changes
- files changed
- commands run
- runtime verification
- browser verification
- remaining limitations

Never claim unverified behavior as working.