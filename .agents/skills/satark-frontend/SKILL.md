---
name: satark-frontend
description: Use when implementing or reviewing SATARK frontend code under frontend/. Covers the zone-based disaster-response Digital Twin, Flood and Earthquake scenarios, people/agent evacuation, simulation playback, impact, risk, cascade, recommendations, and intervention UI.
---

# SATARK Frontend Engineering Skill

## Purpose

This skill governs implementation of SATARK's React/TypeScript frontend.

The frontend is a disaster-response command center around an existing Three.js Digital Twin.

---

## Domain

The simulation is zone-based.

The operator interacts primarily with zones.

Buildings are not individually inspectable simulation entities.

Only two calamities exist:

- Flood
- Earthquake

Agents represent people.

There is no vehicle subsystem.

Safe zones are predefined by the backend.

---

## Core Experience

The frontend should support the operational narrative:

NORMAL CITY
→ CALAMITY
→ AFFECTED ZONE
→ IMPACT
→ AGENT EVACUATION
→ SAFE ZONE
→ CASCADE / RISK
→ RECOMMENDATION
→ APPROVAL
→ UPDATED WORLD

Features should contribute to this narrative rather than becoming disconnected UI.

---

## Backend Authority

Backend determines:

- simulation outcome
- affected zones
- safe zones
- agent states
- agent destinations
- impact
- cascade
- risk
- recommendations
- intervention results

Frontend visualizes these results.

Never recreate backend algorithms in React.

---

## Zone UX

Zone selection and zone state should be obvious.

Use the zone as the primary spatial interaction unit.

Avoid building-level UI.

---

## Agent UX

Agents are people.

Visualize backend-provided state and movement.

Do not create an independent behavioral simulation.

---

## Simulation UX

The operator should be able to:

1. configure a supported scenario
2. run it
3. observe progress
4. replay snapshots
5. understand impact
6. review recommendations
7. approve interventions

Do not invent unsupported scenario controls.

---

## Implementation

Before coding:

- inspect existing files
- inspect actual types/contracts
- identify affected components
- identify affected state
- identify API dependencies
- identify renderer dependencies

Implement the smallest complete feature.

Verify it in the browser.