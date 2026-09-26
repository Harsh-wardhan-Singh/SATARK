# SATARK — Current System Architecture & Implementation Report

> **Date**: 2026-09-13  
> **System Status**: Fully Operational Digital Twin Prototype  
> **Scope**: Comprehensive documentation of all currently implemented subsystems, mathematical models, file architectures, data pipelines, and UI visualizations across the SATARK codebase.

---

## 1. System Overview & Core Philosophy

**SATARK** (Sensing, Analytics, Topographic Assessment & Real-time Knowledge) is a zone-based disaster-response digital twin system. It integrates physical hazard models, machine-learning impact forecasting, critical infrastructure cascading dependencies, human population evacuation behaviors, composite risk scoring, and automated decision-support recommendations into an interactive 3D command-center interface.

```
                  ┌───────────────────────────────────────────┐
                  │          DISASTER SCENARIO INIT           │
                  │   Flood (Rainfall) / Earthquake (PGA)     │
                  └─────────────────────┬─────────────────────┘
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │         PHYSICAL & ML HAZARD LAYER        │
                  │   FloodPropagator / SeismicDamageEngine   │
                  │         FloodImpactPredictor (RF)         │
                  └─────────────────────┬─────────────────────┘
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │      INFRASTRUCTURE CASCADE (DAG)         │
                  │   ExplainableNetwork (Power→Water→Hosp)   │
                  └─────────────────────┬─────────────────────┘
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │          HUMAN RESPONSE PIPELINE          │
                  │    PanicEngine → Evacuation (Dijkstra)    │
                  │    Crowd Dynamics → Casualties Engine     │
                  │    250 HumanAgent Cohorts (3D Movement)   │
                  └─────────────────────┬─────────────────────┘
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │       COMPOSITE RISK & DECISION LAYER     │
                  │     RiskEngine (Weighted 4-Factor Score)  │
                  │  Interventions (Pumps, Power, Reroute)    │
                  │   OptimizationEngine (Counterfactuals)    │
                  └─────────────────────┬─────────────────────┘
                                        │ (DRF REST API)
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │     HOLOGRAPHIC 3D COMMAND CENTER (UI)    │
                  │   Three.js WebGL / Custom Shaders / GTAO  │
                  │   Voronoi 21-Zone Overlay / 3D Agents     │
                  │   React 18 + Zustand + Workflow Panels    │
                  └───────────────────────────────────────────┘
```

### Key Architectural Principles Already Enforced:
1. **Backend Authoritative**: The backend owns all simulation mechanics, agent physics, risk formulas, and safe-zone determinations. The frontend never computes safe zones or hazard steps; it consumes and visualizes authoritative backend state.
2. **Zone-Based Spatial Discretization**: The city domain is discretized into **21 topological zones (`Z01`–`Z21`)**, derived from KMeans clustering of 3D geometry centroids from the master `city.glb` asset.
3. **Representative Cohort Agents**: Rather than individual agent simulation of 250,000 citizens, the population is modeled via **250 deterministic `HumanAgent` cohorts**, each carrying weighted cohort counts and navigating zone-to-zone toward safe shelters.
4. **Separation of Transport and Domain Logic**: Domain state is maintained in-memory within `WorldState`, cleanly decoupled from Django models and serialized via DRF serializers.

---

## 2. Complete Repository File Structure

```
SATARK/
├── backend/
│   ├── agents/                             # Agent cohort modeling & manager
│   │   ├── agent.py                        # HumanAgent entity (NORMAL→PANIC→SAFE)
│   │   ├── apps.py                         # Django app config
│   │   ├── manager.py                      # AgentManager (spawning, movement, intake)
│   │   ├── movement.py                     # 3D vector math (move_toward, reached)
│   │   ├── normal_behavior.py              # Waypoint wandering for calm agents
│   │   └── panic_behavior.py               # Target navigation & speed multiplier
│   ├── algorithms/                         # Pure mathematical & domain algorithms
│   │   ├── casualties/
│   │   │   └── estimation.py               # Multi-vector fatality/injury calculations
│   │   ├── earthquake/
│   │   │   ├── damage.py                   # Lognormal structural fragility curves
│   │   │   └── intensity.py                # Haversine distance + Esteva PGA attenuation
│   │   ├── flood/
│   │   │   ├── impact.py                   # Feature builder adapting state to ML model
│   │   │   └── propagation.py              # Inter-zone elevation-gradient water model
│   │   ├── infrastructure/
│   │   │   ├── cascade.py                  # ExplainableNetwork DAG failure propagation
│   │   │   ├── dependency.py               # Dependency relationships
│   │   │   └── vulnerability.py            # Physical vulnerability scoring
│   │   ├── intervention/
│   │   │   ├── recommendations.py          # Rule-based intervention engine
│   │   │   └── risk_assessment.py          # Component threshold evaluation
│   │   └── population/
│   │       ├── crowd.py                    # Density, bottleneck & congestion ratios
│   │       ├── evacuation.py               # Dijkstra shortest path to safe shelters
│   │       └── panic.py                    # Blackout & hazard panic escalation
│   ├── api/                                # Django REST Framework HTTP Layer
│   │   ├── apps.py                         # API app config
│   │   ├── serializers.py                  # WorldStateSerializer & request validators
│   │   ├── urls.py                         # 12 simulation & intervention endpoints
│   │   └── views.py                        # APIViews (Initialize, Step, Pause, State)
│   ├── calamities/                         # Calamity wrappers
│   │   ├── base.py                         # Abstract Calamity base class
│   │   ├── earthquake.py                   # Earthquake scenario wrapper
│   │   └── flood.py                        # Flood scenario wrapper
│   ├── config/                             # Django project configuration
│   │   ├── asgi.py & wsgi.py               # Application gateways
│   │   ├── settings.py                     # CORS, DRF, middleware, and app settings
│   │   └── urls.py                         # Root URL routing to /api/
│   ├── core/                               # System-wide primitives & types
│   │   ├── constants.py                    # Speeds, default tick rates, thresholds
│   │   ├── enums.py                        # AgentState, CalamityType, SeverityLevel
│   │   └── types.py                        # Position, SimulationConfig dataclasses
│   ├── data/                               # Authoritative JSON datasets
│   │   ├── glb_zone_mapping.json           # 21 zones (coordinates, bounds, neighbors)
│   │   ├── infrastructure.json             # 6 critical nodes with DAG dependencies
│   │   ├── population.json                 # 250,000 residents weighted across 21 zones
│   │   ├── shelters.json                   # 3 municipal shelters with capacities
│   │   └── raw/
│   │       └── flood_model_training.csv    # 10,000 rows synthetic training data
│   ├── decision/                           # Decision-making & counterfactuals
│   │   ├── intervention.py                 # Intervention & CandidateIntervention models
│   │   ├── optimizer.py                    # What-if simulation forking & evaluation
│   │   ├── priority.py                     # Urgency ranking engine
│   │   ├── recommendation.py               # Decision-layer structured recommendations
│   │   └── response.py                     # Action execution parameters
│   ├── ml/                                 # Machine Learning subpackage
│   │   ├── dataset_generator.py            # Synthetic training data generator
│   │   ├── evaluate.py                     # Cross-validation & regression metrics
│   │   ├── features.py                     # Canonical 7-feature schema & normalizers
│   │   ├── flood_impact_model.joblib       # Trained RandomForest model (~36 MB)
│   │   ├── predict.py                      # Runtime inference wrapper
│   │   └── train.py                        # Scikit-learn model trainer
│   ├── risk/                               # Composite risk assessment
│   │   └── risk_engine.py                  # 4-factor composite weighted risk engine
│   ├── scripts/
│   │   └── validate_data.py                # Integrity validator for zone geometry JSON
│   ├── simulation/                         # Core simulation lifecycle
│   │   ├── clock.py                        # SimulationClock with deterministic ticks
│   │   ├── engine.py                       # Orchestrator (4,443 lines)
│   │   ├── scenario.py                     # Immutable Scenario dataclass
│   │   └── world.py                        # SimulationWorld wrapper around state
│   ├── tests/                              # Automated test suite (32 tests)
│   └── twin/                               # Digital Twin state representation
│       ├── entity.py                       # Base Entity class with Position
│       ├── state.py                        # WorldState in-memory store
│       └── twin.py                         # DigitalTwin controller
├── frontend/
│   ├── public/
│   │   └── city.glb                        # 3D GLB city mesh asset
│   └── src/
│       ├── api/                            # Frontend API client layer
│       │   ├── agentApi.ts                 # Agent snapshot fetching
│       │   ├── client.ts                   # Fetch wrapper with error handling
│       │   ├── simulationApi.ts            # Simulation control HTTP calls
│       │   └── worldApi.ts                 # Zone, safe zone, and bounds loader
│       ├── city/                           # Three.js 3D city engine
│       │   ├── CityInteraction.ts          # Mouse raycasting, zone click & hover
│       │   ├── CityRenderer.ts             # Holographic WebGL Three.js renderer
│       │   ├── CityStateAdapter.ts         # Bridge syncing backend state into 3D
│       │   ├── agents/
│       │   │   ├── agentInitialization.ts  # Cohort positions from backend
│       │   │   └── AgentRenderer.ts        # Instanced 3D cohort rendering
│       │   ├── calamities/
│       │   │   ├── DisasterRenderer.ts     # Master calamity visual coordinator
│       │   │   ├── earthquake/EarthquakeRenderer.ts # Epicenter rings & ground shake
│       │   │   └── flood/FloodRenderer.ts  # Water plane mesh & depth extrusion
│       │   ├── camera/
│       │   │   └── CameraController.ts     # OrbitControls, smooth zone focusing
│       │   ├── infrastructure/
│       │   │   └── InfrastructureRenderer.ts# 3D status beacons on critical assets
│       │   ├── utils/
│       │   │   ├── spatial.ts              # Nearest-zone centroid detection
│       │   │   └── terrainFootprint.ts     # Convex hull extraction from GLB terrain
│       │   └── zones/
│       │       ├── voronoi.ts              # Sutherland-Hodgman 2D Voronoi clipper
│       │       └── ZoneRenderer.ts         # Voronoi boundary lines & polygon fills
│       ├── components/                     # React UI components
│       │   ├── digitalTwin/
│       │   │   └── ZonePanel.tsx           # Selected zone telemetry sidebar
│       │   ├── layout/
│       │   │   ├── CommandCenterLayout.tsx # Grid layout container
│       │   │   ├── CommandHeader.tsx       # Status bar, mode selector, clock
│       │   │   └── TimelineBar.tsx         # Simulation playback timeline
│       │   ├── simulation/
│       │   │   ├── DevSimulationControls.tsx# Manual step/run debug panel
│       │   │   └── SimulationControls.tsx  # Play/Pause/Reset triggers
│       │   ├── telemetry/
│       │   │   └── StatusBar.tsx           # Ping, tick rate, active entities
│       │   ├── twin/
│       │   │   └── CityScene.tsx           # React wrapper mounting Three.js canvas
│       │   └── workflow/
│       │       ├── CompactControls.tsx     # Calamity trigger buttons (Flood/Quake)
│       │       ├── LeftPanel.tsx           # Zone config & live disaster monitor
│       │       ├── RightPanel.tsx          # Risk cards & intervention approval
│       │       ├── SimulationLoopManager.tsx# Auto-stepping clock hook
│       │       └── ZoneConfiguration.tsx   # Custom scenario parameter sliders
│       ├── pages/
│       │   └── CommandCenter.tsx           # Master view composition
│       ├── store/                          # Zustand state slices
│       │   ├── agentSlice.ts               # Cohort positions and states
│       │   ├── index.ts                    # Combined useStore hook
│       │   ├── simulationSlice.ts          # Simulation lifecycle & playback
│       │   ├── uiSlice.ts                  # Selected zone & workflow state
│       │   └── worldSlice.ts               # Zones, bounds, environment state
│       ├── types/
│       │   ├── agent.ts                    # AgentState & HumanAgent DTOs
│       │   ├── domain.ts                   # Zone, WorldSnapshot, Risk, Subsystems
│       │   └── simulation.ts               # SimulationConfig, Scenario parameters
│       └── utils/
│           ├── agentValidation.ts          # Schema validation for incoming agents
│           └── snapshotValidation.ts       # Defensive validation of API payloads
├── report.md                               # System audit against competition rules
├── optimisations.md                        # Master optimization and cleanup plan
└── requirements.txt                        # Python dependencies
```

---

## 3. Subsystem Implementation Deep-Dive

### 3.1 Digital Twin State Engine (`backend/twin/`, `backend/simulation/`)

The Digital Twin maintains an authoritative, deterministic world representation in memory:

- **`WorldState` (`twin/state.py`)**:
  - `entities: Dict[str, Entity]`: Spatial objects with unique IDs and 3D logical coordinates $(x, y, z)$.
  - `simulation_time: float`: Authoritative elapsed seconds.
  - `current_tick: int`: Discrete step count.
  - `active_calamity: Optional[CalamityType]`: Current hazard (`FLOOD` or `EARTHQUAKE`).
  - `environment: Dict[str, Any]`: Structured domain state (water levels, infrastructure capacity, panic scores, risk assessments, active interventions).
  - `metrics: Dict[str, float]`: Time-series scalar tracking (e.g. `total_fatalities`, `avg_panic`).
  - `events: List[dict]`: Chronological event log.
- **`SimulationClock` (`simulation/clock.py`)**:
  - Enforces deterministic discrete-time progression.
  - Delta time: $\Delta t = \frac{1.0}{\text{tick\_rate}}$.
  - Advances simulation time and protects against runaway execution (capped at `MAX_SIMULATION_TICKS = 10,000`).
- **`SimulationEngine` (`simulation/engine.py`)**:
  - Master orchestrator governing the lifecycle: `initialize()` $\to$ `step()` $\to$ `pause()` $\to$ `resume()` $\to$ `reset()`.
  - Coordinates state handoffs across all 8 specialized algorithm engines.

---

### 3.2 Calamity Simulation Layer

#### A. Urban Flood Simulation (`algorithms/flood/`, `calamities/flood.py`)
- **Discrete Zone Flow Model**:
  - Operates over the 21 zones mapped in `glb_zone_mapping.json`.
  - Each zone maintains:
    - Ground elevation: derived from normalized mesh coordinates (`center_normalized.y`).
    - Water level: depth above ground in abstract meters.
    - Adjacency: neighboring zone IDs.
    - Drainage capacity: base drainage rate ($0.05\text{ m/hr}$).
- **Propagation Mechanics (`FloodPropagator.simulate_hour`)**:
  1. **Rainfall Influx & Drainage**:
     $$W_i' = \max\left(0, W_i + \text{rainfall} - (\text{drainage} + \text{boost})\right)$$
  2. **Hydraulic Head & Gradient Matrix**:
     $$H_i = Z_i + W_i'$$
     $$\nabla H_{ij} = \frac{\max(0, H_i - H_j)}{d_{ij}} \quad \forall j \in \text{Adj}(i)$$
  3. **D8 Surface Routing (Steepest Descent / Multi-Directional)**:
     - Steepest descent selects $\arg\max_j \nabla H_{ij}$ to concentrate runoff along natural drainage channels.
  4. **Strict Mass Conservation & Outflow Clamping**:
     $$Q_{i}^{\text{demand}} = \sum_{j} q_{ij}$$
     $$\alpha_i = \min\left(1.0, \frac{W_i'}{Q_{i}^{\text{demand}} + \epsilon}\right)$$
     $$F_{ij} = \alpha_i q_{ij}$$
     $$W_i^{\text{next}} = W_i' + \sum_{j} F_{ji} - \sum_{j} F_{ij}$$
     Guarantees $\sum_i (\text{Inflow}_i - \text{Outflow}_i) \equiv 0$ down to machine precision ($\le 10^{-12}$, $0.00\%$ mass creation error).
  5. **Metric Resolution**: Reports both normalized meters ($m$) and real-world centimeters ($cm$).

#### B. Earthquake Seismic Simulation (`algorithms/earthquake/`, `calamities/earthquake.py`)
- **Seismic Intensity Engine (`SeismicEngine.calculate_pga`)**:
  - Computes Peak Ground Acceleration (PGA) in units of $g$ for each zone using an Esteva-style attenuation law:
  1. Great-circle surface distance via the **Haversine formula**:
     $$d = 2R \arcsin \left( \sqrt{\sin^2(\Delta \phi / 2) + \cos(\phi_1)\cos(\phi_2)\sin^2(\Delta \lambda / 2)} \right)$$
  2. Hypocentral 3D distance accounting for focal depth ($h$):
     $$R_{\text{hypo}} = \sqrt{d^2 + h^2}$$
  3. Attenuation and Soil Amplification:
     $$\text{PGA} = \min \left( 2.5, \frac{0.015 \cdot 10^{0.432 M}}{(R_{\text{hypo}} + 0.1)^{1.22}} \cdot \text{soil\_factor} \right)$$
- **Structural Damage Engine (`SeismicDamageEngine.calculate_structural_damage`)**:
  - Evaluates HAZUS-style lognormal fragility curves for 4 distinct damage states: *Slight*, *Moderate*, *Extensive*, and *Complete Collapse*:
    $$P(D \ge d_i \mid \text{PGA}) = \Phi \left( \frac{\ln(\text{PGA} / \theta_i)}{\beta} \right)$$
    Where medians $\theta_i = [0.15, 0.30, 0.55, 0.85] \cdot \text{resilience}$ and dispersion $\beta = 0.4$.
  - Converts cumulative probabilities into mutually exclusive state percentages and outputs structural capacity drops for critical infrastructure.

---

### 3.3 Machine Learning Impact Prediction (`backend/ml/`)

Rather than relying purely on simplified physics, SATARK incorporates a trained machine-learning model to evaluate complex multi-variable flood exposure:

- **Canonical 7-Feature Schema (`ml/features.py`)**:
  1. `elevation`: Normalized terrain height $[0, 1]$.
  2. `flood_exposure`: Scaled water level $\min(1.0, \text{water\_depth} / 2.0)$.
  3. `severity`: Scenario severity index $(1, 2, 3)$.
  4. `day`: Elapsed simulation day.
  5. `intervention`: Active intervention intensity $[0, 1]$.
  6. `drainage_weakness`: $\min(1.0, 1.0 - \text{drainage\_capacity})$.
  7. `infra_vuln`: Inherent zone infrastructure vulnerability rating.
- **Model Architecture & Training (`ml/train.py`)**:
  - **Algorithm**: `RandomForestRegressor` with 100 estimators, maximum depth of 12, and random state 42.
  - Trained on 10,000 rows of synthetic scenario data (`flood_model_training.csv`).
  - Serialized to `backend/ml/flood_impact_model.joblib` (~36 MB).
- **Runtime Inference (`ml/predict.py`, `algorithms/flood/impact.py`)**:
  - `FloodImpactEngine` constructs feature vectors for all 21 zones and executes batch predictions, producing a normalized impact score $[0.0, 1.0]$ per zone.

---

### 3.4 Infrastructure Dependency Cascade (`algorithms/infrastructure/cascade.py`)

Models the cascading collapse of critical urban services during disaster events using an explainable Directed Acyclic Graph (DAG):

- **Infrastructure Assets (`data/infrastructure.json`)**:
  1. `power_station_main`: Central Thermal Power Plant (`Z01`).
  2. `power_poles_lowland`: Lowland Grid Lines (`Z02`, depends on `power_station_main`).
  3. `telecom_tower_1`: Emergency Comms Tower (`Z02`, depends on `power_poles_lowland`).
  4. `water_pumping_station`: District Water Treatment (`Z03`, depends on `power_poles_lowland`).
  5. `hospital_general`: City General Hospital (`Z04`, multi-parent dependency on Power, Water, and Comms).
  6. `main_bridge_access`: River Access Bridge (`Z02`, transport choke point).
- **Cascade Propagation Logic (`ExplainableNetwork.simulate_timestep`)**:
  1. **Direct Physical Hazard**: If local hazard impact exceeds node `vulnerability_threshold`:
     $$\text{damage} = (\text{impact} - \text{threshold}) \times 2.0, \quad \text{local\_health} = \max(0.0, 1.0 - \text{damage})$$
  2. **Dependency Cascade**: Computes weighted operational health of upstream parent nodes:
     $$\text{dep\_score} = \sum (\text{parent\_capacity} \times \text{weight})$$
     Applies backup power damping:
     $$\text{dep\_health} = \text{backup\_power} + (1.0 - \text{backup\_power}) \times \text{dep\_score}$$
  3. **Final Node Capacity**:
     $$\text{capacity} = \text{local\_health} \times \text{dep\_health}$$
  4. **Human-Readable Explainability**: Generates precise diagnostic strings for the operator UI:
     - `"Fully Operational"`
     - `"Direct Flood Damage (Impact: 0.72)"`
     - `"Cascading failure: Lost connection to Lowland Grid Lines"`

---

### 3.5 Human Evacuation & Population Dynamics

#### A. Panic Escalation Engine (`algorithms/population/panic.py`)
- Tracks psychological stress $[0.0, 1.0]$ across all 21 zones based on 3 factors:
  1. **Physical Hazard**: Water depth or seismic ground shaking.
  2. **Infrastructure Blackout Stress**: Loss of local electrical power and communications:
     $$\text{isolation\_stress} = 1.0 - \text{average\_local\_infrastructure\_capacity}$$
  3. **Crowd Density Escalator**:
     $$\text{density\_multiplier} = 1.0 + (\text{zone\_population\_weight} \times 2.0)$$
  - **Update Formula**:
    $$\Delta \text{Panic} = ((\text{hazard} \times 0.4) + (\text{isolation} \times 0.3)) \times \text{density\_multiplier}$$
    If safe and powered, panic slowly calms ($\Delta \text{Panic} = -0.1$).

#### B. Evacuation Route Optimization (`algorithms/population/evacuation.py`)
- Executes **Dijkstra's Algorithm** over the topological zone graph to route populations from endangered zones to designated safe shelters:
  - Valid shelters (`S1` in `Z04`, `S2` in `Z13`, `S3` in `Z20`) are checked for flood accessibility (shelters with water $> 0.4\text{ m}$ are automatically closed).
  - Dynamic Edge Weights:
    $$\text{Travel Cost} = 1.0 + (\text{water\_depth} \times 5.0) + (\text{panic\_level} \times 2.0)$$
  - If water depth exceeds $0.8\text{ m}$, the road is classified as completely blocked and removed from the routing graph.

#### C. Crowd Bottleneck Dynamics (`algorithms/population/crowd.py`)
- Evaluates inter-zone arterial flow capacity.
- Detects bottlenecks when the number of evacuees attempting to traverse a zone edge exceeds transit throughput capacity ($\text{congestion\_ratio} > 1.2$).

#### D. Casualty Estimation Engine (`algorithms/casualties/estimation.py`)
- Calculates cumulative injuries and fatalities across 3 casualty vectors:
  1. **Environmental Flood**: Drowning and swift-water sweep scaled cubically with water depth ($v_{\text{water}}^3$).
  2. **Crowd Dynamics**: Stampede and crush casualties occurring when extreme bottlenecks ($\text{ratio} > 1.2$) intersect with severe panic ($\text{panic} > 0.5$).
  3. **Structural Collapse**: Earthquake structural debris crushing derived from fragility complete-collapse ratios.
  4. **Medical Degradation Multiplier**: If `hospital_general` loses power or capacity, casualty mortality rates spike proportionally.

#### E. Agent Cohort Physics (`agents/agent.py`, `agents/manager.py`)
- Represents the 250,000 residents using **250 representative `HumanAgent` cohorts**.
- **Finite State Machine**:
  $$\text{NORMAL} \xrightarrow{\text{zone panic} \ge 0.5} \text{PANIC} \xrightarrow{\text{reach shelter}} \text{SAFE}$$
- **Physical Movement**:
  - Normal state: wandering waypoints within resident zone.
  - Panic state: moves at double speed ($2.0\text{ m/s}$) along Dijkstra evacuation route positions.
  - Safe state: increments shelter occupant intake counts and deactivates movement.

---

### 3.6 Composite Risk & Decision Support Layer

#### A. Multi-Factor Risk Assessment (`risk/risk_engine.py`)
- Evaluates an explainable composite risk index $[0, 100]$:
  $$\text{Composite Risk} = 0.35 \cdot C_{\text{casualties}} + 0.25 \cdot I_{\text{infrastructure}} + 0.20 \cdot F_{\text{flooding}} + 0.20 \cdot B_{\text{congestion}}$$
- Maps scores to actionable operational severity labels:
  - `0 - 25`: **LOW** (Normal monitoring)
  - `25 - 50`: **MODERATE** (Advisory warnings)
  - `50 - 75`: **HIGH** (Mobilize emergency assets)
  - `75 - 100`: **CRITICAL** (Mandatory evacuation, life hazard)

#### B. Decision & Intervention Rule Engine (`algorithms/intervention/recommendations.py`)
- Evaluates risk breakdown scores and generates targeted emergency interventions:
  1. `deploy_mobile_pumps`: Triggered when flood risk $> 40$; adds $+0.05\text{ m/hr}$ drainage capacity to target zone.
  2. `reroute_traffic`: Triggered when congestion risk $> 30$; expands road transit capacity by $+40\%$.
  3. `deploy_backup_generators`: Triggered when infrastructure failure $> 30$; guarantees a $50\%$ operational floor for hospitals and pumps.
  4. `mandatory_evacuation_order`: Triggered when overall risk $> 70$; accelerates agent evacuation movement speeds by $+50\%$.

#### C. Counterfactual Optimization Engine (`decision/optimizer.py`)
- Evaluates whether a proposed intervention is worthwhile by **forking the simulation**:
  1. Clones the current scenario into an isolated evaluation engine.
  2. Steps the baseline simulation to completion.
  3. Steps candidate intervention simulations to completion.
  4. Computes comparative deltas: lives saved, infrastructure damage prevented, and cost-benefit ratios.

---

### 3.7 REST API Layer (`backend/api/`)

Built using Django REST Framework, exposing 12 simulation control and telemetry endpoints:

| Endpoint | Method | Functionality |
|----------|--------|---------------|
| `/api/simulation/initialize/` | `POST` | Creates and initializes a new in-memory `SimulationEngine`. |
| `/api/simulation/state/` | `GET` | Returns full authoritative snapshot (entities, environment, metrics, events). |
| `/api/simulation/step/` | `POST` | Advances the simulation clock by one tick and runs all pipeline steps. |
| `/api/simulation/run/` | `POST` | Executes ticks continuously until scenario duration is reached. |
| `/api/simulation/pause/` | `POST` | Pauses active tick progression. |
| `/api/simulation/resume/` | `POST` | Resumes active tick progression. |
| `/api/simulation/reset/` | `POST` | Wipes in-memory world state back to tick 0. |
| `/api/simulation/risk/` | `GET` | Returns the current composite risk score and breakdown. |
| `/api/simulation/recommendations/` | `GET` | Returns ranked emergency interventions. |
| `/api/simulation/optimize/` | `POST` | Runs counterfactual baseline-vs-intervention evaluations. |
| `/api/simulation/intervention/` | `POST` | Applies a user-selected intervention to the running engine. |
| `/api/simulation/intervention/apply-selected/` | `POST` | Commits the top recommended intervention. |

---

### 3.8 Frontend 3D Command Center (`frontend/src/`)

A high-performance command-center interface built with **React 18**, **TypeScript**, **Vite**, **Zustand**, and **Three.js**:

```
+----------------------------------------------------------------------------------------------------+
|                                    COMMAND HEADER (Status, Clock, Mode)                            |
+--------------------------+----------------------------------------------------+--------------------+
|        LEFT PANEL        |              3D CITY VIEWPORT (Three.js)           |    RIGHT PANEL     |
| - Zone Telemetry (Z01)   | - Holographic Shaders, Glitch Bands, Fresnel Glow  | - Composite Risk   |
| - Custom Parameter Sliders| - 21-Zone Sutherland-Hodgman Voronoi Overlay       |   Assessment       |
| - Live Casualty Counter  | - 250 Instanced Population Agents (State Colored)  | - Ranked Emergency |
| - Hospital Power Monitor | - 3D Flood Plane Extrusion / Earthquake Shake      |   Recommendations  |
|                          | - Interactive Raycasting Click & Camera Focus      | - One-Click Action |
|                          | - Compact Calamity Triggers (Flood / Earthquake)   |   Interventions    |
+--------------------------+----------------------------------------------------+--------------------+
|                                TIMELINE BAR (Playback Controls, Scrubbing)                         |
+----------------------------------------------------------------------------------------------------+
```

#### A. Holographic Three.js Renderer (`city/CityRenderer.ts`)
- Loads master `city.glb` asset.
- **Custom Holographic Shaders**:
  - Vertex shader creates rhythmic vertical glitch pulses:
    $$\text{glitch} = \sin(y \cdot 0.035 + 3t) \cdot \sin(x \cdot 0.08 + 4t) \cdot 0.35$$
  - Fragment shader blends cyber-purple base with vibrant cyan Fresnel rims and dynamic violet scanlines:
    $$\text{fresnel} = (1.0 - |\mathbf{n} \cdot \mathbf{v}|)^2$$
- **Cinematic Post-Processing Pipeline**:
  - `EffectComposer` chaining `RenderPass`, `GTAOPass` (Ground Truth Ambient Occlusion for building depth), `UnrealBloomPass` (emissive neon glow), and `OutputPass`.

#### B. 21-Zone Voronoi Boundary Layer (`city/zones/voronoi.ts`, `ZoneRenderer.ts`)
- Uses **Sutherland-Hodgman convex polygon clipping** against the terrain boundary footprint.
- Computes exact bisector half-planes between all 21 zone centers.
- Generates 3D boundary line loops and translucent zone polygon fills that dynamically tint based on flood depth or seismic PGA.

#### C. Instanced Agent Rendering (`city/agents/AgentRenderer.ts`)
- Visualizes 250 population cohorts in real time.
- Color-coded by state:
  - **Cyan / Blue**: `NORMAL` (Calm, navigating local zone)
  - **Vibrant Orange / Red**: `PANIC` (Actively evacuating along Dijkstra routes)
  - **Emerald Green**: `SAFE` (Reached designated shelter)

#### D. Interactive Camera & Controls (`city/camera/CameraController.ts`, `CityInteraction.ts`)
- Orbit controls with constrained polar angles preventing camera flip.
- Raycasting detects hovered and clicked zones, smoothly animating the camera to focus on selected city sectors.

#### E. State Synchronization Loop (`components/workflow/SimulationLoopManager.tsx`)
- Automatic tick runner executing periodic HTTP requests to `/api/simulation/step/`.
- Synchronizes backend snapshots into the unified Zustand store, driving telemetry panels and 3D visualizers without lag.

---

### 3.9 Authoritative Data Inventory (`backend/data/`)

| File | Content & Purpose |
|------|-------------------|
| `glb_zone_mapping.json` | 21 zones (`Z01`–`Z21`) with 3D world coordinates, normalized coords, neighbor adjacency graph, and map boundaries ($X: [-327, 342], Z: [-287, 383]$). |
| `infrastructure.json` | 6 critical infrastructure assets with DAG dependencies, vulnerability thresholds, and backup power configurations. |
| `population.json` | 250,000 residents distributed across 21 zones weighted proportionally by building footprint proxies. |
| `shelters.json` | 3 municipal emergency shelters (`S1` in `Z04`, `S2` in `Z13`, `S3` in `Z20`) with aggregate capacity of 70,000 evacuees. |
| `raw/flood_model_training.csv` | 10,000 synthetic training rows covering elevation, flood depth, severity, drainage weakness, and impact targets. |
| `city.glb` (in `frontend/public/`) | Production 3D city mesh model containing terrain, road networks, and building geometries. |

---

## 4. End-to-End Execution Flow (A Complete Simulation Tick)

To understand how all implemented components cooperate during runtime:

```
[OPERATOR] Clicks "TRIGGER FLOOD" (Rainfall = 40 mm/hr, Duration = 24h)
    │
    ▼
[FRONTEND] POST /api/simulation/initialize/ ──► Backend instantiates SimulationEngine
    │
    ▼
[SimulationLoopManager] Starts periodic POST /api/simulation/step/
    │
    ├── 1. SimulationClock advances (simulation_time += delta_time, tick += 1)
    │
    ├── 2. Flood.step() ──► FloodPropagator computes elevation-gradient water levels
    │
    ├── 3. FloodImpactEngine ──► Normalizes 7 features ──► RandomForest predicts ML impact [0, 1]
    │
    ├── 4. ExplainableNetwork ──► Evaluates direct damage & cascades power loss to Hospital
    │
    ├── 5. PanicEngine ──► Escalates zone panic from rising water & power blackout
    │
    ├── 6. EvacuationEngine ──► Dijkstra routes evacuees away from flooded paths to Shelters
    │
    ├── 7. CasualtiesEngine ──► Estimates injuries & fatalities (water + crowd crush + hospital drop)
    │
    ├── 8. AgentManager ──► Transitions cohort agents (NORMAL ──► PANIC ──► SAFE) & updates 3D positions
    │
    ├── 9. RiskEngine ──► Computes composite risk score (e.g. 74.2 - HIGH) & explainable breakdown
    │
    ├── 10. RecommendationEngine ──► Generates "Deploy Mobile Pumps" & "Reroute Traffic"
    │
    └── 11. WorldStateSerializer serializes complete state ──► HTTP 200 Response
    │
    ▼
[FRONTEND ZUSTAND STORE] applyWorldSnapshot(snapshot)
    │
    ├── ZoneRenderer: Tints Z02 and Z03 red/blue to reflect water accumulation
    ├── FloodRenderer: Rises 3D water plane over lowland sectors
    ├── AgentRenderer: Animates orange cohort particles fleeing along Dijkstra paths
    ├── InfrastructureRenderer: Turns substation beacon from green to flashing red
    ├── LeftPanel: Updates live casualty counter, time remaining, and zone flood depth
    └── RightPanel: Displays 74.2 Risk Score and enables "Approve Mobile Pumps" button
```

---

## 5. Summary of Achievements

SATARK has already achieved an end-to-end operational pipeline:
1. **Fully Integrated Backend Architecture**: End-to-end chain from physical hazard inputs through ML prediction, DAG cascades, agent movement, risk calculation, and counterfactual optimization.
2. **Dual-Calamity Foundation**: Physics and damage fragility equations implemented for both Flood and Earthquake scenarios.
3. **High-Fidelity 3D Holographic UI**: Custom Three.js city visualization featuring post-processed ambient occlusion, bloom, custom procedural shaders, Voronoi zone clipping, and instanced agent animations.
4. **Data-Driven Digital Twin**: Authoritative, reproducible geospatial coordinates, infrastructure graphs, population allocations, and shelter facilities cleanly mapped to 3D geometry.
5. **Decoupled Architecture**: Clean separation between backend simulation authority and frontend command-center visualization.
