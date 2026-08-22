---
trigger: always_on
---

# SATARK Core Project Rules

## 1. PROJECT IDENTITY

This repository contains SATARK, a disaster-response digital-twin system.

SATARK consists of at least two major subsystems:

- backend
- frontend

The backend is responsible for authoritative simulation/domain logic.

The frontend is responsible for the command-center interface and visualization.

The two subsystems must remain clearly separated.

---

# 2. SHARED DOMAIN MODEL

SATARK is a ZONE-BASED disaster simulation.

Zones are the primary spatial unit of the simulation.

Individual buildings are NOT the primary simulation unit.

Buildings may exist inside the 3D city representation, but they are not individually simulated or individually inspected by the operator.

Do NOT introduce building-level simulation or inspection unless explicitly requested by the project owner.

---

# 3. SUPPORTED CALAMITIES

SATARK currently supports exactly two calamity types:

- Flood
- Earthquake

Do not add other calamities unless explicitly requested.

Do not introduce:
- tsunami
- wildfire
- cyclone
- tornado
- landslide
- generic future calamity abstractions

merely because they appear useful.

---

# 4. AGENTS

Agents represent people in the simulated environment.

There is no separate vehicle simulation system.

Do not introduce:
- vehicle entities
- vehicle managers
- vehicle modes
- vehicular agents
- emergency vehicle systems
- vehicle routing

unless explicitly requested.

Agent behavior is determined by the authoritative simulation/backend.

---

# 5. SAFE ZONES

Safe zones are predefined by the backend.

The frontend must not calculate or infer safe zones.

Do not determine safe zones using:
- elevation calculations
- distance calculations
- terrain analysis
- proximity
- pathfinding
- frontend heuristics

The backend determines which zones are safe and, where applicable, the destination toward which agents evacuate.

The frontend visualizes this authoritative information.

---

# 6. BACKEND AUTHORITY

The backend is authoritative for domain and simulation logic.

The frontend must not independently recreate:

- disaster simulation
- impact calculation
- cascade calculation
- risk calculation
- optimization
- safe-zone selection
- agent behavioral simulation
- recommendation generation
- intervention optimization

The frontend consumes authoritative backend results and visualizes them.

The backend must not depend on frontend-only assumptions for core domain behavior.

---

# 7. DO NOT INVENT CONTRACTS

Never silently invent:

- API endpoints
- request fields
- response fields
- database entities
- simulation behavior
- domain states
- recommendation logic
- backend algorithms

If the required backend contract is unknown, identify the missing information.

Do not fabricate a permanent implementation merely to make the frontend/backend compile.

Clearly isolated mock data may be used for frontend development when necessary, but it must remain obviously mock data and must not be mistaken for the real backend contract.

---

# 8. FRONTEND / BACKEND BOUNDARY

The repository has two primary development areas:

backend/
frontend/

The frontend developer/agent should normally modify:

frontend/**

The backend developer/agent should normally modify:

backend/**

Do not modify the other subsystem without a concrete reason.

If a shared contract or configuration must change:

1. identify the reason
2. explain the affected subsystem
3. make the smallest necessary change
4. verify both sides where possible

---

# 9. SHARED FILES

Files at the repository root and shared configuration are collaborative resources.

Do not casually modify:

- .gitignore
- package management configuration
- repository configuration
- CI configuration
- shared documentation
- API contract documentation

without considering the other subsystem.

If a change is required, explain why it is required.

---

# 10. GIT SAFETY

Do not reset, revert, delete, or rewrite another developer's work.

Do not use destructive Git operations unless explicitly instructed.

Never discard uncommitted changes merely because they appear unrelated.

Before substantial work:

- inspect git status
- understand the current branch
- understand existing modifications

Preserve work belonging to other developers.

---

# 11. COLLABORATIVE DEVELOPMENT

Assume another developer may be working in the repository simultaneously.

Do not assume that an unfamiliar change is an error.

Before overwriting a file with existing modifications:

1. inspect the modifications
2. determine whether they belong to the current task
3. preserve unrelated work

Prefer additive, targeted changes over broad rewrites.

---

# 12. CHANGE DISCIPLINE

For every substantial task:

1. inspect the existing implementation
2. identify the relevant files
3. understand dependencies
4. formulate a plan
5. make the smallest correct change
6. verify the change
7. check for regressions

Do not perform unrelated refactors.

Do not rewrite working systems merely because another architecture appears cleaner.

---

# 13. QUALITY STANDARD

Generated code must be maintainable and production-quality.

Avoid:

- unnecessary abstractions
- duplicated logic
- dead code
- fake implementations presented as real
- unnecessary dependencies
- unexplained magic numbers
- unsafe type handling
- giant monolithic modules
- silent error handling
- speculative features

Prefer:

- clear responsibilities
- explicit contracts
- small targeted changes
- useful types
- meaningful names
- verifiable behavior

---

# 14. COMPLETION STANDARD

A task is not complete merely because code was generated.

Where applicable:

- typecheck
- lint
- build
- run
- test
- inspect runtime behavior
- inspect errors
- verify affected functionality

If something could not be verified, explicitly state that.

Never claim that an unverified feature works.