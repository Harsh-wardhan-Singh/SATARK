---
name: satark-ui
description: Use when designing or implementing SATARK command-center UI under frontend/, including Dashboard, Digital Twin controls, zone status, simulation controls, impact, risk, cascade, recommendations, and intervention approval.
---

# SATARK UI Skill

## Visual Goal

SATARK should feel like a professional disaster-response command center.

The interface should be:

- technical
- focused
- modern
- information-dense
- controlled
- readable

The 3D city remains the visual focus.

---

## Information Hierarchy

Prioritize:

1. active calamity
2. affected zone
3. severity/risk
4. population impact
5. evacuation
6. simulation state
7. recommendation
8. intervention

Do not create a wall of disconnected metrics.

---

## Zone-First Interface

Use zones as the main spatial interaction unit.

Do not create building-inspection UI.

---

## Safe Zones

Clearly distinguish backend-defined safe zones from affected zones.

Do not imply that the frontend discovered or calculated them.

---

## Controls

Controls should clearly communicate:

- current scenario
- affected zone
- simulation state
- current playback position
- available action

---

## Feedback

Asynchronous actions require visible feedback.

Examples:

Run Simulation
→ Running
→ Complete / Error

Approve Intervention
→ Processing
→ Result
→ Updated state

---

## 3D Viewport

Keep the city visually dominant.

Avoid unnecessary overlays.

Only show overlays that improve understanding:

- zone boundaries
- zone labels
- safe zones
- evacuation
- calamity
- important impact state

---

## Accessibility

Use:

- readable labels
- sufficient contrast
- meaningful status indicators
- keyboard-accessible controls where practical
- clear error messages

Do not rely on color alone for critical state.