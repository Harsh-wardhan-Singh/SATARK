---
trigger: glob
---

# SATARK Frontend Architecture Rules

## SCOPE

These rules apply only to the SATARK frontend.

The frontend is located under:

frontend/

Do not apply these rules to backend-only work.

---

# 1. CORE STACK

The frontend uses:

- React
- TypeScript
- Vite
- Three.js
- Zustand
- React Router

Use the existing project stack.

Do not replace the frontend framework or 3D architecture without explicit approval.

Do not introduce React Three Fiber merely because React is being used.

The existing city renderer is native Three.js and should remain so.

---

# 2. FRONTEND RESPONSIBILITIES

The frontend is responsible for:

- command-center UI
- navigation
- Digital Twin presentation
- zone visualization
- safe-zone visualization
- agent visualization
- calamity visualization
- simulation controls
- simulation playback
- impact visualization
- risk visualization
- cascade visualization
- recommendation presentation
- intervention approval UI
- loading states
- error states
- responsive behavior
- accessibility

The frontend is NOT responsible for independently simulating the disaster.

---

# 3. TARGET STRUCTURE

The frontend follows this conceptual structure:

src/
├── api/
├── types/
├── store/
├── pages/
├── components/
├── city/
└── utils/

Responsibilities:

api/
    Backend communication.

types/
    Domain and API types.

store/
    Zustand application state.

pages/
    Route-level composition.

components/
    Reusable UI.

city/
    Three.js rendering subsystem.

utils/
    General frontend utilities.

---

# 4. REACT / THREE.JS SEPARATION

React owns:

- pages
- layouts
- forms
- panels
- controls
- charts
- status displays
- recommendation UI
- intervention UI

Three.js owns:

- scene
- renderer
- camera
- lights
- meshes
- materials
- shaders
- post-processing
- 3D city
- 3D zones
- 3D agents
- 3D calamity effects
- 3D evacuation visualization

Do not make React responsible for thousands of individual Three.js objects.

Do not put the entire Three.js scene into React state.

---

# 5. API LAYER

Backend requests belong primarily under:

src/api/

Avoid scattering raw fetch calls throughout UI components.

Prefer:

UI
↓
store/action
↓
API function
↓
backend

Do not invent API endpoints.

Use the actual backend contract when available.

---

# 6. STATE MANAGEMENT

Zustand is the primary frontend state-management system.

The intended conceptual stores are:

## twinStore

Current Digital Twin state:

- zones
- safe zones
- agents
- infrastructure state
- calamity state
- other authoritative world state

## simulationStore

Simulation state:

- scenario
- snapshots
- current tick
- playback state
- playback speed
- simulation results
- baseline/intervention results where supported

## uiStore

UI state:

- selected zone
- active panel
- modal state
- transient interface state

Do not put every piece of application data into one global store.

---

# 7. DOMAIN ENTITIES

The primary frontend entities are:

- Zone
- SafeZone
- Agent
- Infrastructure
- Calamity
- Simulation
- Impact
- Recommendation

Do not introduce a primary interactive Building entity.

Do not introduce a Vehicle entity.

---

# 8. ZONE-FIRST INTERACTION

The operator interacts primarily with zones.

Typical interactions may include:

- selecting a zone
- viewing zone status
- selecting an affected zone for a simulation
- viewing zone severity
- viewing evacuation
- viewing safe zones

Do not build building-level inspection interfaces.

---

# 9. SAFE-ZONE VISUALIZATION

Safe zones originate from backend data.

The frontend visualizes them.

The frontend must not calculate them.

Do not implement frontend elevation analysis or safe-zone discovery.

---

# 10. AGENT VISUALIZATION

Agents represent people.

The renderer may visualize:

- current position
- state
- destination
- evacuation
- safe arrival

The frontend should visualize authoritative state rather than simulate agent behavior independently.

---

# 11. SIMULATION PLAYBACK

The backend may provide simulation snapshots.

The frontend is responsible for:

- loading snapshots
- selecting the current snapshot/tick
- play
- pause
- restart
- playback speed
- timeline/scrubbing where supported

Do not fabricate authoritative simulation state between snapshots.

Visual interpolation may be used for smooth rendering when appropriate, but it must not change the underlying simulation state.

---

# 12. PERFORMANCE

The frontend contains a performance-sensitive Three.js application.

Avoid:

- unnecessary React rerenders
- per-frame object allocations
- repeated GLTF loading
- repeated texture loading
- duplicated geometry
- duplicated materials
- unnecessary post-processing
- unnecessary raycasting
- uncontrolled object creation

Prefer reuse, caching, stable references, and explicit lifecycle management.

---

# 13. MOCK DATA

Mock data is permitted for frontend development when backend contracts are unavailable.

However:

- isolate mock data
- label it clearly
- do not spread mock assumptions throughout the codebase
- do not present mock behavior as backend behavior
- replace mocks with real contracts when available

---

# 14. NO UNRELATED REFACTORING

When implementing a frontend feature:

Do not refactor unrelated frontend systems.

Do not reorganize the entire codebase merely because a different organization seems preferable.

Preserve existing working behavior.

---

# 15. FRONTEND / BACKEND COLLABORATION

If a frontend feature requires a backend change:

1. identify the required contract
2. document the requirement
3. avoid silently modifying backend code
4. coordinate the backend change
5. implement against the agreed contract

Do not create frontend workarounds that permanently encode an incorrect backend model.