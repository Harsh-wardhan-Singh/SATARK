# SATARK — System Long-Term Memory & Working Context
## Urban Flood Nowcasting System (Drainage and Rainfall Coupling)

> **Version**: 2.0.0 (Authoritative Self-Contained Working Memory)  
> **Last Updated**: 2026-09-13  
> **Purpose**: This document is the single source of truth for the entire SATARK digital twin codebase. It contains complete class registries, mathematical formulations, API schemas, file directory maps, technical debt tracking, and phase roadmaps. All subsequent prompts will consult and update this memory file directly.

---

## 1. System Identity, Core Philosophy & Rules

- **Project**: SATARK (Sensing, Analytics, Topographic Assessment & Real-time Knowledge).
- **Core Domain**: Urban Flood Nowcasting System (Drainage and Rainfall Coupling).
- **Calamity Scope**: **100% FLOOD ONLY**. Earthquake has been completely removed from backend and frontend.
- **Primary Spatial Unit**: 21 Topological Zones (`Z01`–`Z21`) derived from building geometry centroids of `city.glb`.
- **Primary Agent Unit**: 250 `HumanAgent` cohorts representing ~250,000 citizens.
- **Backend Authority**: Backend is strictly authoritative for physics, simulation stepping, flood propagation, agent FSM transitions, risk scoring, safe zone designations, and recommendations. Frontend ONLY visualizes.
- **Zero Invented Contracts**: Never invent API endpoints or payload formats; adhere strictly to DRF specifications.

---

## 2. Complete Repository File & Directory Registry

### Legend:
- `[ACTIVE]`: Operational production code.
- `[DEAD-DELETE]`: Unreferenced dead code / scaffold to be deleted in Phase 0.
- `[MODIFY]`: Active code that needs modification.
- `[NEW]`: Module to be implemented in upcoming phases### 2.1 Backend Structure (`c:\Users\sitak\SATARK\backend\`)

```
backend/
├── agents/
│   ├── agent.py               [ACTIVE] 8.2 KB - HumanAgent dataclass (NORMAL, PANIC, SAFE)
│   ├── apps.py                [ACTIVE] 150 B - Django app configuration
│   ├── manager.py             [ACTIVE] 19.2 KB - AgentManager (cohort spawning, movement, intake)
│   ├── movement.py            [ACTIVE] 3D vector math (move_toward, distance)
│   ├── normal_behavior.py     [ACTIVE] 1.7 KB - NormalBehavior (wandering within zone)
│   └── panic_behavior.py      [ACTIVE] 2.5 KB - PanicBehavior (navigation toward nearest shelter)
│
├── algorithms/
│   ├── casualties/
│   │   └── estimation.py      [ACTIVE] 6.0 KB - CasualtiesEngine (flood casualty estimation)
│   ├── drainage/              [ACTIVE - Phase 2]
│   │   ├── __init__.py        [ACTIVE] Package init & exports
│   │   ├── network.py         [ACTIVE] DrainageNetwork (34 nodes, 33 pipes, pumps, outfalls)
│   │   ├── hydraulics.py      [ACTIVE] ManningHydraulicsEngine (pipe flow, capacity, surcharge)
│   │   └── coupling.py        [ACTIVE] CoupledDrainageModel (surface-drainage dual layer exchange)
│   ├── flood/
│   │   ├── impact.py          [MODIFY] 4.9 KB - FloodImpactEngine (vectorize with NumPy arrays)
│   │   └── propagation.py     [ACTIVE - Phase 3] 8.4 KB - FloodPropagator (mass conservation & D8 routing)
│   ├── infrastructure/
│   │   ├── cascade.py         [ACTIVE] 4.0 KB - ExplainableNetwork (authoritative DAG failure engine)
│   │   ├── dependency.py      [ACTIVE] 2.0 KB - DependencyBuilder
│   │   └── vulnerability.py   [ACTIVE] 4.3 KB - InfrastructureNetwork
│   ├── intervention/
│   │   ├── recommendations.py [ACTIVE] 6.7 KB - InterventionRuleEngine
│   │   └── risk_assessment.py [ACTIVE] 4.2 KB - RiskAssessmentEngine
│   ├── navigation/            [ACTIVE - Phase 5]
│   │   ├── __init__.py        [ACTIVE] Package exports (FloodSafeNavigationEngine, RouteResult)
│   │   └── router.py          [ACTIVE] FloodSafeNavigationEngine (risk-weighted Dijkstra avoiding >30cm water)
│   ├── population/
│   │   ├── crowd.py           [ACTIVE] 4.8 KB - CrowdDynamicsEngine (congestion ratios & bottlenecks)
│   │   ├── evacuation.py      [ACTIVE] 3.3 KB - EvacuationEngine (Dijkstra pathfinding to shelters)
│   │   └── panic.py           [ACTIVE] 3.2 KB - PanicEngine (zone-level panic calculation)
│   └── rainfall/              [ACTIVE - Phase 4]
│       ├── __init__.py        [ACTIVE] Package exports (HyetographEngine, NowcastEngine)
│       ├── hyetograph.py      [ACTIVE] HyetographEngine (Chicago storm, SCS Type II, IMD radar curves)
│       └── nowcast.py         [ACTIVE] NowcastEngine (0-3h forward state projection)
│
├── api/
│   ├── apps.py                [ACTIVE] 144 B - APIConfig
│   ├── serializers.py         [ACTIVE] 7.3 KB - DRF serializers (WorldStateSerializer, request schemas)
│   ├── urls.py                [ACTIVE] DRF url routing (includes navigation & world endpoints)
│   └── views.py               [ACTIVE] 12.5 KB - APIViews (simulation lifecycle, twin, agents, world)
│
├── calamities/
│   ├── base.py                [ACTIVE] 2.0 KB - Abstract Calamity base class
│   └── flood.py               [ACTIVE] 5.5 KB - Flood calamity wrapper
│
├── config/
│   ├── settings.py            [ACTIVE] Django settings (configured for DRF & CORS)
│   └── urls.py                [ACTIVE] Root URL routing to /api/
│
├── core/
│   ├── constants.py           [ACTIVE] Simulation constants & speeds
│   ├── enums.py               [ACTIVE] CalamityType (FLOOD only)
│   └── types.py               [ACTIVE] Position, SimulationConfig
│
├── data/
│   ├── glb_zone_mapping.json  [ACTIVE] 21 zones geometry, centroids, and neighbor adjacency
│   ├── infrastructure.json    [ACTIVE] 6 critical infrastructure nodes with DAG dependencies
│   ├── population.json        [ACTIVE] 250,000 population weights across 21 zones
│   ├── shelters.json          [ACTIVE] 3 municipal shelters with capacities and positions
│   ├── drainage_network.json  [ACTIVE - Phase 2] Synthetic pipe network topology (34 nodes, 33 pipes)
│   ├── maps/                  [ACTIVE] Spatial boundary and map assets
│   ├── scenarios/             [ACTIVE] Pre-configured flood scenarios
│   ├── synthetic/             [ACTIVE] Synthetic benchmark datasets
│   └── raw/
│       └── flood_model_training.csv [ACTIVE] 10,000 rows synthetic training data
│
├── decision/
│   ├── intervention.py        [ACTIVE] 2.6 KB - Intervention, CandidateIntervention
│   ├── optimizer.py           [MODIFY] 15.2 KB - OptimizationEngine (cache model, eliminate 180MB unpickling)
│   ├── priority.py            [ACTIVE] 6.8 KB - PriorityEngine
│   ├── recommendation.py      [ACTIVE] 9.8 KB - RecommendationEngine (decision ranker)
│   └── response.py            [ACTIVE] 2.1 KB - ResponseEngine
│
├── infrastructure/
│   └── facility.py            [ACTIVE] 2.6 KB - Facility model (used by agents for shelters)
│
├── ml/
│   ├── dataset_generator.py   [MODIFY] Update with drainage & surcharge features
│   ├── evaluate.py            [ACTIVE] Regression evaluation
│   ├── features.py            [ACTIVE] Canonical 7-feature schema
│   ├── flood_impact_model.joblib [ACTIVE] ~36 MB trained RandomForest model
│   ├── predict.py             [MODIFY] 3.6 KB - FloodImpactPredictor (implement singleton cache)
│   └── train.py               [MODIFY] Model training pipeline (optionally LightGBM in Phase 6)
│
├── risk/
│   └── risk_engine.py         [ACTIVE] 16.3 KB - RiskEngine (composite 35/25/20/20 weighted risk)
│
├── scripts/
│   └── validate_data.py       [ACTIVE] 7.9 KB - Data integrity & schema validator
│
├── simulation/
│   ├── clock.py               [ACTIVE] 1.4 KB - SimulationClock
│   ├── scenario.py            [ACTIVE] 3.3 KB - Scenario dataclass
│   ├── world.py               [ACTIVE] 1.7 KB - SimulationWorld wrapper
│   ├── engine.py              [ACTIVE] 68.2 KB (2,537 lines) - Decomposed orchestrator; uses SimulationPipeline
│   └── pipeline/              [ACTIVE - Phase 1 & 1.5]
│       ├── __init__.py        [ACTIVE] Package exports SimulationPipeline and all steps
│       ├── base_step.py       [ACTIVE] SimulationStep protocol & StepContext
│       ├── rainfall_step.py   [ACTIVE] Step 1: Authoritative rainfall rate injection
│       ├── drainage_step.py   [ACTIVE] Step 2: Stormwater drainage & Manning pipe stepping
│       ├── surface_step.py    [ACTIVE] Step 3: Authoritative surface water flow & live intervention
│       ├── impact_step.py     [ACTIVE] Step 4: ML zone flood impact scoring
│       ├── cascade_step.py    [ACTIVE] Step 5: Infrastructure dependency DAG evaluation & cascade interventions
│       ├── evacuation_step.py [ACTIVE] Step 6: Dijkstra routing, crowd dynamics, shelter intake, casualty reduction
│       ├── risk_step.py       [ACTIVE] Step 7: Composite risk scoring (35/25/20/20 weights)
│       ├── decision_step.py   [ACTIVE] Step 8: Priority evaluation, algorithmic recommendations, intervention flags
│       └── metrics_step.py    [ACTIVE] Step 9: Authoritative global metrics & tick events
│
├── tests/
│   ├── conftest.py            [ACTIVE] Pytest fixtures & test configuration
│   ├── test_agent_visualization.py [ACTIVE] Integration tests
│   ├── test_casualties.py     [ACTIVE] Casualties engine unit tests
│   ├── test_drainage.py       [ACTIVE] Manning formula, network topology, pump boost, and pipeline coupling tests
│   ├── test_infrastructure.py [ACTIVE] ExplainableNetwork DAG tests
│   ├── test_intervention_regression.py [ACTIVE] Intervention regression test suite
│   ├── test_pipeline.py       [ACTIVE] 9-step simulation pipeline unit tests
│   ├── test_population.py     [ACTIVE] Crowd & evacuation engine tests
│   ├── test_risk_pipeline.py  [ACTIVE] Risk engine pipeline tests
│   └── test_simulation.py     [ACTIVE] Deterministic engine stepping tests
│
└── twin/
    ├── entity.py              [ACTIVE] 637 B - Base Entity
    ├── manager.py             [ACTIVE] 2.1 KB - TwinManager
    ├── state.py               [ACTIVE] 4.9 KB - WorldState
    └── twin.py                [ACTIVE] 1.7 KB - DigitalTwin
```

---

### 2.2 Frontend Structure (`c:\Users\sitak\SATARK\frontend\src\`)

```
frontend/src/
├── api/
│   ├── agentApi.ts            [ACTIVE] 1.5 KB - Agent snapshots
│   ├── client.ts              [MODIFY] 2.0 KB - ApiClient (make URL env-driven, add put/patch/delete)
│   ├── simulationApi.ts       [ACTIVE] 3.0 KB - Simulation lifecycle calls
│   └── worldApi.ts            [MODIFY] 2.5 KB - Zone & shelter calls
│
├── city/
│   ├── CityInteraction.ts     [ACTIVE] 4.0 KB - Raycasting and zone clicks
│   ├── CityRenderer.ts        [ACTIVE] 53.0 KB (1,387 lines) - Three.js scene, camera, materials, render loop
│   ├── CityStateAdapter.ts    [ACTIVE] 5.9 KB - Bridges Zustand to Three.js
│   ├── agents/
│   │   ├── agentInitialization.ts [ACTIVE] 5.2 KB - Cohort coordinate setup
│   │   └── AgentRenderer.ts   [ACTIVE] 23.3 KB - Instanced cohort rendering & animation
│   ├── calamities/
│   │   ├── DisasterRend│   ├── impact/                [NEW/REFILL - Phase 7]
│   │   ├── RiskBreakdownCard.tsx [NEW] Casualties, infra, flood, congestion gauges (from RightPanel)
│   │   ├── CascadeStatusCard.tsx [NEW] Infrastructure failure DAG display (from RightPanel)
│   │   └── EvacuationMetricsCard.tsx [NEW] Shelter intake & congestion (from RightPanel)
│   ├── layout/
│   │   ├── CommandCenterLayout.tsx [ACTIVE] 750 B - Grid layout container
│   │   ├── CommandHeader.tsx  [ACTIVE] 181 B - Top navigation bar & clock
│   │   ├── TimelineBar.tsx    [ACTIVE] 175 B - Simulation playback timeline
│   │   └── StatusBar.tsx      [ACTIVE] Real-time engine telemetry bar
│   ├── recommendations/       [NEW/REFILL - Phase 7]
│   │   ├── RecommendationCard.tsx [NEW] Recommendation item (from RightPanel)
│   │   └── InterventionActionModal.tsx [NEW] Approval & counterfactual diffs (from RightPanel)
│   ├── simulation/
│   │   ├── DevSimulationControls.tsx [ACTIVE] 2.6 KB - Debug stepping panel
│   │   ├── SimulationControls.tsx [ACTIVE] 394 B - Play/pause triggers
│   │   ├── RainfallSlider.tsx [NEW - Phase 7] Hyetograph storm intensity controls (from ZoneConfig)
│   │   └── NowcastSlider.tsx  [NEW - Phase 7] 0-3h forecast scrubber
│   ├── twin/
│   │   ├── CityScene.tsx      [ACTIVE] 6.7 KB - Three.js canvas wrapper
│   │   └── CityScene.css      [ACTIVE] Canvas layout styles
│   └── workflow/
│       ├── CompactControls.tsx [ACTIVE] 1.9 KB - Floating HUD buttons
│       ├── LeftPanel.tsx      [ACTIVE] 6.5 KB - Flood monitor & log
│       ├── RightPanel.tsx     [ACTIVE] 9.2 KB - Active telemetry & interventions
│       ├── SimulationLoopManager.tsx [ACTIVE] 3.1 KB - Auto-stepping loop
│       └── ZoneConfiguration.tsx [ACTIVE] 8.8 KB - Zone flood config controls
│
├── pages/
│   └── CommandCenter.tsx      [ACTIVE] 1.0 KB - Master single-screen view composition
│
├── store/
│   ├── index.ts               [ACTIVE] 687 B - useAppStore (composed root store)
│   ├── agentSlice.ts          [ACTIVE] 2.8 KB - Agent cohort state
│   ├── simulationSlice.ts     [ACTIVE] 2.6 KB - Simulation lifecycle state
│   ├── uiSlice.ts             [ACTIVE] 1.3 KB - WorkflowState
│   └── worldSlice.ts          [ACTIVE] 476 B - Zones, shelters, bounds
│
├── types/
│   ├── agent.ts               [ACTIVE] 2.6 KB - AgentState, HumanAgent DTOs
│   ├── domain.ts              [ACTIVE] 813 B - Zone, SafeZone, FloodEnvironment (CalamityType = 'FLOOD')
│   └── simulation.ts          [ACTIVE] 2.3 KB - SimulationMetadata, WorldSnapshot
│
└── utils/
    ├── agentValidation.ts     [ACTIVE] 4.4 KB - Agent payload validator
    ├── snapshotValidation.ts  [ACTIVE] 3.3 KB - Snapshot validator
    └── spatial.ts             [ACTIVE] 1.0 KB - Spatial utils
```

---

## 3. Mathematical Models & Algorithmic Specifications

### 3.1 Urban Flood Propagation (Revised Mass-Conserving Model)
- **Current Defect**: Neighbor height comparisons are asynchronous and outflows uncapped $\to$ non-conservative water creation.
- **Authoritative Formulation**:
  Let $H_i = Z_i + W_i$ be the hydraulic head (elevation $Z_i$ + water depth $W_i$).
  Directed flow from zone $i$ to neighbor $j$ over timestep $\Delta t$:
  $$q_{i \to j} = \max\left(0, k \cdot (H_i - H_j)\right)$$
  Total outward demand from zone $i$:
  $$Q_i = \sum_{j \in \mathcal{N}_i} q_{i \to j}$$
  Strict outflow clamping factor:
  $$\alpha_i = \min\left(1.0, \frac{W_i}{Q_i + \epsilon}\right)$$
  Conserved actual outflow:
  $$f_{i \to j} = \alpha_i \cdot q_{i \to j}$$
  Mass-conserving depth update:
  $$W_i(t + \Delta t) = W_i(t) + \left( R_i - D_i + \sum_{j \in \mathcal{N}_i} f_{j \to i} - \sum_{j \in \mathcal{N}_i} f_{i \to j} \right) \cdot \Delta t$$
  $$\text{Net Mass Balance Error} \equiv \sum_i \Delta W_i - \sum_i (R_i - D_i) \cdot \Delta t = 0.00\%$$

### 3.2 Stormwater Drainage Network & Manning's Pipe Hydraulics
- **Network Graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$**:
  - Nodes $\mathcal{V}$: Manholes, catchbasins, pumping stations, outfalls.
  - Edges $\mathcal{E}$: Storm pipes, underground conduits, open canals.
- **Pipe Flow Capacity (Manning's Equation)**:
  $$Q_{\text{cap}} = \frac{1}{n} \cdot A \cdot R_h^{2/3} \cdot S^{1/2}$$
  Where:
  - $n$: Manning's roughness coefficient (concrete pipe: $0.013$, corrugated metal: $0.024$).
  - $A$: Cross-sectional flow area ($\text{m}^2$). For full circular pipe of diameter $D$: $A = \frac{\pi D^2}{4}$.
  - $R_h$: Hydraulic radius ($\text{m}$). For full circular pipe: $R_h = \frac{D}{4}$.
  - $S$: Bed slope ($\Delta z / L$).
- **Surcharge & Backflow Condition**:
  - When inflow $Q_{\text{in}} > Q_{\text{cap}}$, excess water backs up:
    $$Q_{\text{surcharge}} = \max(0, Q_{\text{in}} - Q_{\text{cap}})$$
  - Surcharged water pushes back through manhole inlets onto surface streets.

### 3.3 Temporal Rainfall Hyetographs
- **Time-varying rainfall intensity $I(t)$**:
  - **Chicago Design Storm**: Symmetrical peak rainfall profile around peak time $t_p$.
  - **SCS Type II Distribution**: Standard urban monsoon rainfall distribution curve.
  - Hyetograph time horizon: 0 to 180 minutes ($0–3\text{ hours}$).

### 3.4 0–3 Hour Nowcasting Engine
- Given active state $\mathcal{S}_t = \text{WorldState}(t)$:
  - Fork $\mathcal{S}_t \to \mathcal{S}_{\text{fork}}$.
  - Step forward under rainfall hyetograph $I(t)$ to generate projections:
    - $t + 60\text{ min} \to \mathcal{P}_{1\text{h}}$
    - $t + 120\text{ min} \to \mathcal{P}_{2\text{h}}$
    - $t + 180\text{ min} \to \mathcal{P}_{3\text{h}}$
  - Output: Array of `{ zone_id, water_depth_cm, surcharge_volume, flooded_streets }` for each hour.

### 3.5 Human Evacuation & Dijkstra Route Navigation
- **Road / Zone Graph $\mathcal{G}_{\text{evac}}$**:
  - Edge cost between zone $A$ and $B$:
    $$C(A, B) = \text{Distance}(A, B) \cdot \left(1.0 + 5.0 \cdot W_B + 2.0 \cdot \text{Panic}_B\right)$$
  - Road impassable condition: $W_B > 0.8\text{ m}$ (or depth $> 30\text{ cm}$ for vehicle/public routing).
- **Navigation API Route Cost**:
  - Returns shortest flood-safe path avoiding segments where depth $> 30\text{ cm}$.

### 3.6 Machine Learning Impact Prediction (RandomForest)
- **7 Canonical Features**:
  1. `elevation`: Normalized $[0, 1]$
  2. `flood_exposure`: $\min(1.0, \text{depth} / 2.0)$
  3. `severity`: Scenario severity index $(1, 2, 3)$
  4. `day`: Elapsed simulation day
  5. `intervention`: Intensity $[0, 1]$
  6. `drainage_weakness`: $1.0 - \text{drainage\_capacity}$
  7. `infra_vuln`: Inherent zone vulnerability $[0, 1]$
- **Model**: `RandomForestRegressor` (100 trees, depth 12). Serialized to `flood_impact_model.joblib` (36 MB).

### 3.7 Composite Risk Formula
$$\text{Risk} = 0.35 \cdot \text{Casualties} + 0.25 \cdot \text{InfraDamage} + 0.20 \cdot \text{Flooding} + 0.20 \cdot \text{Congestion}$$

---

## 4. Authoritative DRF REST API Catalog

Base URL: `http://localhost:8000/api/`

| Endpoint | Method | Purpose | Request Body / Parameters | Key Response Fields |
|---|---|---|---|---|
| `/simulation/initialize/` | `POST` | Initialize flood scenario | `{"calamity_type": "FLOOD", "rainfall_intensity": 0.8, "duration": 3600, "tick_rate": 1.0}` | Full `WorldState` snapshot |
| `/simulation/state/` | `GET` | Fetch active state | None | `{"current_tick", "simulation_time", "environment", "metrics", "subsystems"}` |
| `/simulation/step/` | `POST` | Advance 1 tick | None | Full `WorldState` snapshot |
| `/simulation/run/` | `POST` | Run to completion | `{"steps": 100}` (optional) | Terminal `WorldState` snapshot |
| `/simulation/pause/` | `POST` | Pause execution | None | `{"status": "PAUSED"}` |
| `/simulation/resume/` | `POST` | Resume execution | None | `{"status": "RUNNING"}` |
| `/simulation/reset/` | `POST` | Reset simulation | None | Reset `WorldState` snapshot |
| `/simulation/risk/` | `GET` | Get risk assessment | None | `{"overall_risk", "components", "zone_risks"}` |
| `/simulation/recommendations/` | `GET` | Get interventions | None | `[{"id", "title", "cost", "lives_saved", "rationale"}]` |
| `/simulation/optimize/` | `POST` | Run counterfactuals | None | `{"best_intervention", "evaluations": [...]}` |
| `/simulation/intervention/` | `POST` | Apply intervention | `{"type": "MOBILE_PUMPS", "target_zone": "Z05"}` | `{"intervention", "state"}` |
| `/simulation/nowcast/` | `GET` | [NEW - Phase 4] 0-3h forecast | None | `{"forecast": [{"t": 1, "depths": {...}}, {"t": 2, ...}, {"t": 3, ...}]}` |
| `/world/zones/` | `GET` | [NEW - Phase 5] Authoritative zones | None | `{"zones": [{"id": "Z01", "bounds": [...], "elevation": 0.2}]}` |
| `/world/shelters/` | `GET` | [NEW - Phase 5] Municipal shelters | None | `{"shelters": [{"id": "shelter_1", "capacity": 500, "coords": [...]}]}` |
| `/navigation/route/` | `POST` | [NEW - Phase 5] Flood-safe route | `{"origin": [lat, lon], "destination": [lat, lon]}` | `{"path": [...], "depth_profile": [...], "safe": true, "travel_time_min": 14}` |

---

## 5. Domain Entities & Spatial Data Specs

### 5.1 21 Topological Zones
- Extracted via KMeans clustering on `city.glb` building geometry centroids.
- Zone IDs: `Z01`, `Z02`, `Z03`, `Z04`, `Z05`, `Z06`, `Z07`, `Z08`, `Z09`, `Z10`, `Z11`, `Z12`, `Z13`, `Z14`, `Z15`, `Z16`, `Z17`, `Z18`, `Z19`, `Z20`, `Z21`.
- Bounds: Coordinate bounding boxes in GLB local units (approx. $-200,000$ to $+200,000$).
- Elevation: Normalized $Y$-coordinate in range $[0.0, 1.0]$.

### 5.2 3 Municipal Safe Shelters
1. `shelter_1`: Zone `Z03`, Capacity: 80,000, Logical coords: `(-120000, 0, 80000)`
2. `shelter_2`: Zone `Z10`, Capacity: 100,000, Logical coords: `(50000, 0, -40000)`
3. `shelter_3`: Zone `Z18`, Capacity: 70,000, Logical coords: `(140000, 0, 120000)`

### 5.3 6 Critical Infrastructure Nodes (DAG)
- `power_station_alpha`: Power supply (Roots the DAG)
- `transmission_grid_main`: Dependent on `power_station_alpha`
- `telecom_tower_north`: Dependent on `power_station_alpha`
- `water_pump_station_central`: Dependent on `power_station_alpha`
- `hospital_city_general`: Dependent on `water_pump_station_central`, `transmission_grid_main`
- `bridge_crossing_east`: Road network arterial

---

## 6. Technical Debt Register & Bug Tracking

| Bug ID | Location | Defect Description | Resolution Plan | Status |
|---|---|---|---|---|
| **LL-1** | `propagation.py:33` | Non-conservative mass flow in flood routing | Symmetrical edge flow bounding $\sum \text{outflow} \le V_i$ | **Resolved (Phase 3)** |
| **LL-2** | `pytest` collection | 14 test failures: missing `pytest.ini`, `core` import errors, stale `Scenario` kwargs | Add `pytest.ini`, `conftest.py`, fix `test_simulation.py` | **Resolved (Phase 0)** |
| **LL-3** | `engine.py:2443` | Blocking debug `print()` inside hot simulation tick | Replace with `logging.getLogger().debug()` | **Resolved (Phase 1)** |
| **LL-4** | `impact.py:161` | Double DataFrame roundtrip on every tick | Vectorize features directly with 2D NumPy array | Open (Phase 6) |
| **LL-5** | `predict.py:64` | 36 MB model loaded from disk 5x in optimizer (180 MB I/O) | Process-level singleton cache `_MODEL_CACHE` | Open (Phase 6) |
| **LL-6** | `engine.py:4238` | Disk read of `glb_zone_mapping.json` on EVERY simulation tick | Cache in `self._cached_zone_mapping` on init | **Resolved (Phase 1)** |
| **LL-7** | `worldApi.ts:8` | Direct cross-boundary import of backend JSON in client bundle | Implement `/api/world/zones/` HTTP endpoint | **Resolved (Phase 5)** |
| **LL-8** | `views.py` | Inconsistent return envelope (`/step/` raw vs `/intervention/` nested) | Standardize on `{status, data, action_result}` | **Resolved (Phase 5)** |
| **LL-9** | `vite.config.ts` | 881 KB monolithic client bundle warning | Add manual rollup chunks (`vendor-three`, `vendor-react`) | Open (Phase 7) |
| **LL-10** | `client.ts:6` | Hardcoded `http://localhost:8000/api` base URL | Use `import.meta.env.VITE_API_URL || '/api'` | Open (Phase 7) |
| **LL-11** | `backend/` root | Loose test scripts crash `manage.py test` with connection errors | Delete loose scripts from `backend/` root | **Resolved (Phase 0)** |
| **LL-12** | `engine.py` | 4,443-line monolithic class with 70 methods | Decompose into `backend/simulation/pipeline/` | **Resolved (Phase 1)** |
| **LL-13** | `RightPanel.tsx` | 320-line monolithic HUD panel | Decompose into `components/impact/` & `recommendations/` | Open (Phase 7) |

---

## 7. Master Serial Implementation Roadmap Tracker

```
[x] Phase 0: Complete Cleanup, Earthquake Elimination & Test Suite Repair (COMPLETED)
    [x] 0.1 Delete 69 frontend empty stubs
    [x] 0.2 Delete backend dead subsystems (cascade/, dead files in infrastructure/, water_model.py, loose scripts)
    [x] 0.3 Completely delete Earthquake files (backend algorithms/earthquake/, calamities/earthquake.py, frontend EarthquakeRenderer.ts)
    [x] 0.4 Remove Earthquake branches (enums.py, engine.py, casualties/estimation.py, domain.ts, uiSlice.ts, panels)
    [x] 0.5 Create pytest.ini and backend/tests/conftest.py
    [x] 0.6 Fix stale constructors in backend/tests/test_simulation.py
    [x] 0.7 Verify 100% passing tests via pytest (36/36 passed) and clean frontend build via npm run build (0 errors)

[x] Phase 1: Pure Flood Modular Pipeline Engine & Subfolder Decomposition (COMPLETED)
    [x] 1.1 Create backend/simulation/pipeline/ base step protocol
    [x] 1.2 Decompose SimulationEngine into 8 discrete step handlers (Rainfall, Drainage, SurfaceFlood, Impact, Cascade, Evacuation, Risk, Decision, Metrics)
    [x] 1.3 Implement in-memory zone mapping cache in initialize() (LL-6 resolved)
    [x] 1.4 Replace raw print() statements with logging (LL-3 resolved)
    [x] 1.5 Verify simulation stepping via automated integration tests (test_pipeline.py added, 40/40 tests passing)

[x] Phase 2: Graph-Based Drainage Network & Manning Hydraulics (COMPLETED)
    [x] 2.1 Implement backend/algorithms/drainage/network.py (nodes, edges, pumps, outfalls)
    [x] 2.2 Implement backend/algorithms/drainage/hydraulics.py (Manning equation, capacity, surcharge)
    [x] 2.3 Implement backend/algorithms/drainage/coupling.py (surface-drainage dual layer transfer)
    [x] 2.4 Create backend/data/drainage_network.json mapped to 21 zones (34 nodes, 33 pipes)
    [x] 2.5 Unit tests in backend/tests/test_drainage.py (7/7 tests passed)

[x] Phase 3: Surface Water Routing & Mass Conservation (COMPLETED)
    [x] 3.1 Rewrite backend/algorithms/flood/propagation.py with mass-conserving edge flow
    [x] 3.2 Implement D8 surface elevation-gradient flow routing
    [x] 3.3 Report water depths in real centimeters (cm)
    [x] 3.4 Unit tests in backend/tests/test_mass_conservation.py (0.00% mass error verification, 6/6 passed)

[x] Phase 4: Temporal Rainfall Hyetographs & 0–3 Hour Nowcasting (COMPLETED)
    [x] 4.1 Implement backend/algorithms/rainfall/hyetograph.py (Chicago storm, SCS Type II curves, radar nowcasting)
    [x] 4.2 Implement backend/algorithms/rainfall/nowcast.py (isolated cloned state for 1h, 2h, 3h projections)
    [x] 4.3 Add GET /api/simulation/nowcast/ endpoint
    [x] 4.4 Unit tests in backend/tests/test_nowcast.py (7/7 passed, 60/60 suite passing)

[x] Phase 5: World REST Endpoints & Flood-Safe Route Navigation API (COMPLETED)
    [x] 5.1 Implement GET /api/world/zones/, /shelters/, /bounds/
    [x] 5.2 Implement POST /api/navigation/route/ (risk-weighted Dijkstra avoiding water > 30cm)
    [x] 5.3 Refactor frontend/src/api/worldApi.ts to consume HTTP endpoints (LL-7 resolved)
    [x] 5.4 Unit tests in backend/tests/test_navigation_api.py (9/9 passed, 69/69 suite passing)

[ ] Phase 6: ML Model Optimization & Vectorized Inference
    [ ] 6.1 Implement singleton model cache in backend/ml/predict.py
    [ ] 6.2 Vectorize feature pipeline in backend/algorithms/flood/impact.py with pure NumPy
    [ ] 6.3 Update dataset generator with drainage capacity & surcharge features
    [ ] 6.4 Train lightweight < 5 MB regressor

[ ] Phase 7: Dynamic GIS Dashboard & Modular UI Components
    [ ] 7.1 Decompose RightPanel.tsx into components/impact/ and components/recommendations/
    [ ] 7.2 Decompose ZoneConfiguration.tsx into components/simulation/
    [ ] 7.3 Implement Leaflet 2D GIS overlay toggle in frontend/src/components/gis/
    [ ] 7.4 Add 0-3h nowcast depth heatmap and forecast slider
    [ ] 7.5 Configure Vite rollup chunk splitting in vite.config.ts

[ ] Phase 8: Real Metro Geospatial Data Integration
    [ ] 8.1 Ingest Mumbai SRTM 30m DEM elevation grid
    [ ] 8.2 Map Mumbai ward-level census populations to zones
    [ ] 8.3 Calibrate against Mumbai 26 July 2005 storm profile (944 mm in 24h)

[ ] Phase 9: Comprehensive Benchmarking & Production Documentation
    [ ] 9.1 Benchmark: 1-hour simulation executes in < 100 ms
    [ ] 9.2 Complete real unit test coverage across all algorithm modules
    [ ] 9.3 Produce production README.md and competition judge methodology documentation
```
