# SATARK Backend ML / Algorithms / Data Audit

## Scope
This document audits the backend files under:
- `backend/ml`
- `backend/algorithms`
- `backend/data`

It also includes the small set of backend orchestration files that determine how the simulation state is expected to move through the system:
- `backend/twin`
- `backend/agents`
- `backend/calamities`
- `backend/decision`
- `backend/api`

The current codebase is mostly a simulation engine with one real ML model for flood impact, plus implemented earthquake intensity/damage logic and a rule-based intervention/risk layer. Several orchestration folders are still scaffolding or partially empty placeholders.

---

## 1) High-level architecture

### Core idea
SATARK is designed as a digital-twin style disaster simulator:
1. Static zone and infrastructure data are loaded from JSON files.
2. Flood state is simulated over zones.
3. Infrastructure capacity is degraded by direct flood and dependency failures.
4. Crowd movement and panic are updated.
5. Evacuation routes are calculated.
6. Casualties are estimated from exposure, congestion, panic, and hospital health.
7. A flood impact ML model predicts a zone-level impact score.
8. A seismic hazard/damage chain can compute earthquake PGA and fragility-based structural damage.
9. Risk assessment and intervention recommendation layers can score the simulation state and suggest mitigation actions.

### Important reality of the current code
- Flood simulation is partially implemented and functional.
- Flood impact ML is implemented and functional, but the feature schema is inconsistent across files.
- Earthquake intensity and structural damage are implemented, but the higher-level calamity orchestration is still absent.
- Risk assessment and recommendation logic exist in the intervention folder, but the broader decision/API layers are mostly empty.
- The digital twin and NPC system exist as in-memory state managers, not as a full simulation service.

---

## 2) Execution order for the flood simulation pipeline

This is the effective order the code expects:

1. Load zone and population data:
   - `backend/data/glb_zone_mapping.json`
   - `backend/data/population.json`
2. Generate or load flood training data:
   - `backend/ml/dataset_generator.py`
   - `backend/data/raw/flood_model_training.csv`
3. Train the flood impact regressor:
   - `backend/ml/train.py`
4. Load the trained model:
   - `backend/ml/predict.py`
   - `backend/algorithms/flood/impact.py`
5. Simulate flood water movement:
   - `backend/algorithms/flood/water_model.py`
   - `backend/algorithms/flood/propagation.py`
6. Predict flood impact per zone:
   - `backend/algorithms/flood/impact.py`
7. Update infrastructure health:
   - `backend/algorithms/infrastructure/vulnerability.py`
   - `backend/algorithms/infrastructure/cascade.py`
8. Update panic:
   - `backend/algorithms/population/panic.py`
9. Compute evacuation routes:
   - `backend/algorithms/population/evacuation.py`
10. Move crowds and detect bottlenecks:
    - `backend/algorithms/population/crowd.py`
11. Estimate casualties:
    - `backend/algorithms/casualties/estimation.py`
12. Evaluate risk and produce interventions:
  - `backend/algorithms/intervention/risk_assessment.py`
  - `backend/algorithms/intervention/recommendations.py`
13. Feed the outputs to response layers:
  - still intended in `backend/decision/*`

---

## 3) Execution order for the earthquake simulation pipeline

This is the intended order and is now partially implemented at the algorithm level:

1. Read earthquake configuration / intensity data.
2. Compute zone shaking intensity.
3. Convert intensity into structural damage.
4. Degrade infrastructure and panic.
5. Estimate casualties and agent evacuation response.

### Current status
- `backend/algorithms/earthquake/intensity.py` implements PGA estimation with attenuation and soil amplification.
- `backend/algorithms/earthquake/damage.py` implements fragility-based structural damage and infrastructure capacity reduction.
- `backend/calamities/earthquake.py` is empty.
- `backend/calamities/tsunami.py` is empty.
- `backend/calamities/base.py` is empty.

So the earthquake calculation model exists, but the higher-level calamity orchestration and integration hooks are still missing.

---

## 4) File-by-file audit

## 4.1 backend/ml

### `backend/ml/dataset_generator.py`
Purpose:
- Generates synthetic training data for the flood impact ML model.

Inputs:
- `load_base_data()` reads:
  - `backend/data/population.json`
  - `backend/data/glb_zone_mapping.json`
- `generate_dataset(zones, samples=10000)` expects:
  - `zones`: dict keyed by zone id
  - `samples`: int

Outputs:
- Writes `backend/data/raw/flood_model_training.csv`
- Prints the number of generated rows

Input / output types:
- `load_base_data() -> dict[str, dict[str, float]]`
- `generate_dataset(...) -> None`
- CSV columns:
  - `zone_id` (string)
  - `elevation` (float)
  - `flood_exposure` (float)
  - `severity` (int)
  - `day` (int)
  - `intervention` (float)
  - `drainage_weakness` (float)
  - `infra_vuln` (float)
  - `impact_score` (float)

Math / classification logic:
- The impact target is a weighted regression formula, not a classifier.
- Formula:
  - `sev_norm = severity / 3.0`
  - `day_norm = day / 7.0`
  - `raw_impact = 0.30*flood_exposure + 0.25*sev_norm + 0.15*drainage_weakness + 0.15*infra_vuln + 0.10*day_norm - 0.25*intervention`
  - Gaussian noise with mean 0 and std 0.02 is added
  - Result is clipped to `[0, 1]`

Notes:
- This is supervised regression generation.
- The formula is intentionally aligned with the current training data, not with the later runtime predictor schema.

---

### `backend/ml/train.py`
Purpose:
- Trains a flood impact regression model.

Inputs:
- Reads `backend/data/raw/flood_model_training.csv`
- Feature columns:
  - `elevation`
  - `flood_exposure`
  - `severity`
  - `day`
  - `intervention`
  - `drainage_weakness`
  - `infra_vuln`
- Target column:
  - `impact_score`

Outputs:
- Trained `RandomForestRegressor`
- Saved model file:
  - `backend/ml/flood_impact_model.joblib`
- Prints MSE and R2

Input / output types:
- `train_model() -> None`

ML details:
- Model: `RandomForestRegressor`
- Parameters:
  - `n_estimators=100`
  - `max_depth=12`
  - `random_state=42`
- Data split:
  - 80% train
  - 20% test
  - `train_test_split(..., random_state=42)`
- Metrics:
  - MSE
  - R2 score

Math / ML behavior:
- This is a tree ensemble regressor.
- It learns nonlinear interactions between the seven features and the synthetic impact target.
- It does not classify discrete labels; it predicts a continuous impact score.

---

### `backend/ml/evaluate.py`
Purpose:
- Evaluates the saved flood model against the full synthetic dataset.
- Also tests a few hand-crafted edge cases.

Inputs:
- Loads `backend/ml/flood_impact_model.joblib`
- Loads `backend/data/raw/flood_model_training.csv`
- Uses the same seven training features as `train.py`

Outputs:
- Prints:
  - MSE
  - MAE
  - R2 score
  - prediction min/max
  - predictions for edge cases

Input / output types:
- `evaluate() -> None`

Math / ML behavior:
- Pure inference and metric calculation.
- Uses `mean_squared_error`, `mean_absolute_error`, `r2_score`.

---

### `backend/ml/predict.py`
Purpose:
- Runtime wrapper around the saved flood impact model.

Inputs:
- Model path defaults to `backend/ml/flood_impact_model.joblib`
- `features_dict` for single prediction
- `zones_feature_list` for batch prediction

Outputs:
- `predict_impact(features_dict) -> float`
- `batch_predict(zones_feature_list) -> list[float]`

Input / output types:
- Single prediction input: `dict[str, Any]`
- Batch prediction input: `list[dict[str, Any]]`
- Output: float or list of float values in `[0, 1]`

ML behavior:
- Creates a pandas DataFrame from input dict(s)
- Calls model.predict
- Clips outputs to `[0, 1]`

Important note:
- The example test features in this file do not match the training schema.
- The example uses fields such as `population_density`, `infra_vulnerability`, `rainfall_severity`, `duration_factor`, `intervention_level`, which are not the same as the training columns.
- This is a major integration bug risk.

---

### `backend/ml/features.py`
Purpose:
- Placeholder only.

Current state:
- Only a docstring
- No functions, no feature engineering logic

---

### `backend/ml/flood_impact_model.joblib`
Purpose:
- Serialized trained ML model artifact.

Notes:
- Binary file.
- Not source code.
- Should be treated as generated output.

---

### `backend/ml/apps.py`
Purpose:
- Django app configuration for the `ml` app.

Inputs:
- None beyond Django app loading.

Outputs:
- Registers the app name as `ml`.

Input / output types:
- No runtime data flow.
- `MLConfig` is a Django `AppConfig` subclass.

Notes:
- This file is infrastructure only.
- It does not affect the ML math.

---

## 4.2 backend/algorithms/flood

### `backend/algorithms/flood/water_model.py`
Purpose:
- Simulates water accumulation and inter-zone flow based on terrain elevation and drainage.

Inputs:
- `zone_data`: dict keyed by zone id, each value should include:
  - `elevation` (float)
  - `drainage_rate` (float)
- `adjacency_list`: dict[str, list[str]]
- `rainfall_mm_per_hour`: float

Outputs:
- `calculate_next_state(...) -> dict[str, float]`
- Returns updated water level per zone

Math / logic:
- Rain conversion:
  - `rain_m = rainfall_mm_per_hour / 1000.0`
- For each zone:
  - `net_water = current_water + rain_m - drainage_rate`
  - `next_levels[zone] = max(0, net_water)`
- Flow model:
  - absolute height = elevation + water depth
  - if current zone is higher than neighbor, water flows outward
  - `flow_volume = min(current_water, gradient * 0.1)`
- This is a simple height-gradient flow approximation.

Notes:
- This is deterministic physics-style simulation, not ML.

---

### `backend/algorithms/flood/propagation.py`
Purpose:
- Alternate flood propagation engine using zone mapping JSON.

Inputs:
- `zone_mapping_path`: path to `glb_zone_mapping.json`
- `rainfall_intensity`: float

Outputs:
- `simulate_hour(rainfall_intensity) -> dict[str, float]`

Input / output types:
- Constructor input: `str`
- Output state: zone id to water level

Math / logic:
- Each hour:
  - add rainfall
  - subtract fixed drainage capacity of 0.05
- Neighbor flow uses:
  - `flow_k = 0.2`
  - `height_diff = my_height - neighbor_height`
  - if diff > 0, outflow increases
  - else inflow increases
- Final level is clamped to nonnegative.

Important note:
- The inflow/outflow model is simpler than `water_model.py` and is not physically consistent with it.
- The two flood engines are overlapping alternatives, not a single unified implementation.

---

### `backend/algorithms/flood/impact.py`
Purpose:
- Uses the ML model to convert flood states and zone metadata into per-zone impact scores.

Inputs:
- `flood_states`: dict[str, float]
- `zones_data`: dict[str, dict]
- `duration_factor`: float
- `intervention_level`: float
- model file path: defaults to `ml/flood_impact_model.joblib`

Outputs:
- `calculate_impacts(...) -> dict[str, float]`

Input / output types:
- Inputs are dictionaries and floats
- Output is zone id to impact score in `[0, 1]`

Feature construction:
- The file’s feature vector is:
  - `flood_exposure`
  - `population_density`
  - `drainage_weakness`
  - `infra_vulnerability`
  - `rainfall_severity`
  - `duration_factor`
  - `intervention_level`

Math / ML behavior:
- `flood_exposure = min(1, water_level / 2.0)`
- `drainage_weakness = 1 - drainage_capacity`
- model.predict is called and result is clipped to `[0, 1]`

Critical note:
- This feature schema does not match the training schema used in `train.py`.
- This is the most important ML integration risk in the repo.

---

## 4.3 backend/algorithms/infrastructure

### `backend/algorithms/infrastructure/dependency.py`
Purpose:
- Builds a directed dependency graph for infrastructure.
- Validates it as a DAG.

Inputs:
- `raw_infrastructure_data`: dict loaded from `backend/data/infrastructure.json`

Outputs:
- `validate_architecture() -> bool`
- `get_critical_paths() -> list[str]`
- internal graph structure in `self.graph`

Math / logic:
- Uses DFS cycle detection with recursion stack.
- Cycles raise `ValueError`.
- Root nodes are those without `depends_on`.

---

### `backend/algorithms/infrastructure/vulnerability.py`
Purpose:
- Simulates infrastructure failure and cascade propagation.

Inputs:
- `infra_file_path`: path to infrastructure JSON
- `flood_states`: dict[str, float]

Outputs:
- `simulate_cascade(...) -> dict`
- Returns formatted node report with:
  - `zone_id`
  - `type`
  - `capacity`
  - `status`

Input / output types:
- Input path: `str`
- Flood state: `dict[str, float]`
- Output: dict keyed by node id, each value is a node status dict

Math / logic:
- Direct flood impact:
  - if `water_level >= vulnerability_threshold`, node drops to `backup_power`
  - else base capacity is 1.0
- Dependency impact:
  - weighted parent capacities are averaged into a dependency ratio
  - `operational_capacity = min(base_capacity, dependency_ratio)`
  - `final_capacity = max(backup_power, operational_capacity)`
- Loops until state stabilizes

Notes:
- This is a cascade simulation, not ML.
- It is stateful and iterative.

---

### `backend/algorithms/infrastructure/cascade.py`
Purpose:
- Explains infrastructure degradation in UI-friendly terms.

Inputs:
- `json_path`: infrastructure JSON path
- `flood_impacts`: dict[str, float] mapping zone id to impact score

Outputs:
- `simulate_timestep(...) -> None`
- `export_for_ui() -> str` JSON string

Input / output types:
- Input impact map: `dict[str, float]`
- UI export: serialized JSON string

Math / logic:
- Local damage:
  - if impact > vulnerability_threshold
  - `damage = (impact - threshold) * 2.0`
  - `local_health = max(0, 1 - damage)`
- Dependency health:
  - weighted parent capacity score with backup power blending
- Final capacity:
  - `final_capacity = local_health * dep_health`
- Then reason text is produced based on whether the failure is local or cascading.

Notes:
- This is the clearest explainable infrastructure model in the repo.

---

## 4.4 backend/algorithms/population

### `backend/algorithms/population/evacuation.py`
Purpose:
- Calculates evacuation routes from each zone to the nearest usable shelter.

Inputs:
- `zones_path`: zone mapping JSON
- `shelters_path`: shelters JSON
- `flood_states`: dict[str, float]
- `panic_states`: dict[str, float]

Outputs:
- `calculate_evacuation_routes(...) -> dict`

Input / output types:
- Inputs are file paths and dictionaries
- Output is a route map keyed by zone id

Math / logic:
- Uses Dijkstra’s algorithm
- Shelter zones are excluded if flood >= 0.4
- Roads are blocked if neighbor flood > 0.8
- Travel cost formula:
  - `1.0 + 5.0*water_penalty + 2.0*panic_penalty`

Notes:
- This is graph search, not ML.
- Route safety is binary, but costs are continuous.

---

### `backend/algorithms/population/crowd.py`
Purpose:
- Simulates movement of people between zones and shelter intake.

Inputs:
- `population_data`: dict from `population.json`
- `shelter_data`: dict from `shelters.json`
- `evacuation_routes`: dict from evacuation engine
- `panic_states`: dict[str, float]

Outputs:
- `simulate_movement_step(...) -> dict`
- Returns:
  - `zone_populations`
  - `shelter_status`
  - `bottlenecks`

Input / output types:
- Input populations and states are dictionaries
- Output is dictionary of dictionaries

Math / logic:
- Movement rate:
  - `0.4 + 0.4 * panic`
  - so up to 80% of a zone may attempt to move per hour
- Transit capacity proxy:
  - `building_footprint_proxy * 0.1`
- Bottleneck score:
  - `incoming_people / capacity`
  - capped at 3.0
- Shelter intake:
  - people outside move into shelter if capacity is available

Notes:
- This is a high-level crowd abstraction.
- It does not simulate individual path physics.

---

### `backend/algorithms/population/panic.py`
Purpose:
- Updates zone-level panic based on flood hazard, infrastructure loss, and population density.

Inputs:
- `population_data`: dict from `population.json`
- `flood_impacts`: dict[str, float]
- `infra_states`: dict from infrastructure engine

Outputs:
- `update_panic(...) -> dict[str, float]`

Input / output types:
- Input: dicts
- Output: panic per zone in `[0, 1]`

Math / logic:
- `density_multiplier = 1.0 + 2.0 * population_weight`
- If hazard > 0.1 or isolation stress > 0.2:
  - `panic_increase = ((hazard_level * 0.4) + (isolation_stress * 0.3)) * density_multiplier`
- Else panic decays by 0.1
- Clamp to `[0, 1]`

Notes:
- Panic is a deterministic state model, not a learned model.

---

## 4.5 backend/algorithms/casualties

### `backend/algorithms/casualties/estimation.py`
Purpose:
- Estimates injuries and fatalities from flood exposure, crowd bottlenecks, panic, and medical system degradation.

Inputs:
- `infrastructure_data`: dict from infrastructure JSON
- `current_populations`: dict[str, int]
- `flood_states`: dict[str, float]
- `bottlenecks`: dict[str, float]
- `panic_states`: dict[str, float]
- `infra_states`: dict from infrastructure simulation

Outputs:
- `update_casualties(...) -> dict`
- Returns:
  - `total_fatalities`
  - `total_injuries`
  - `zone_breakdown`
  - `medical_system_health`

Input / output types:
- Inputs are dictionaries
- Output is dictionary with cumulative counts and breakdowns

Math / logic:
- Medical health:
  - average capacity across hospitals
- Environmental injury rate:
  - `(water_level ** 2) * 0.02`
- Environmental fatality rate:
  - `(water_level ** 3) * 0.005` if water > 0.5 else 0
- Crush injury/fatality rates:
  - only if bottleneck > 1.2 and panic > 0.5
  - injury: `(over_capacity * panic) * 0.03`
  - fatality: `(over_capacity * panic) * 0.002`
- Untreated injury deaths:
  - `int(raw_injuries * ((1 - avg_medical_health) * 0.15))`

Notes:
- This is a deterministic hazard model.
- It is cumulative across ticks.

---

## 4.6 backend/algorithms/earthquake

### `backend/algorithms/earthquake/intensity.py`
Purpose:
- Computes per-zone peak ground acceleration for earthquake events.

Class:
- `SeismicEngine`

Inputs:
- `zone_data: dict`
- `epicenter_lat: float`
- `epicenter_lon: float`
- `magnitude: float`
- `depth_km: float`

Outputs:
- `calculate_pga(...) -> dict[str, float]`

Math / logic:
- Uses the Haversine formula for surface distance.
- Uses hypocentral distance: `sqrt(surface_distance^2 + depth_km^2)`.
- Applies a simplified attenuation relationship:
  - `base_pga = (0.015 * (10 ** (0.432 * magnitude))) / ((hypocentral_distance + 0.1) ** 1.22)`
- Applies soil amplification with `soil_factor`.
- Clamps PGA to `2.5g`.

Notes:
- This is deterministic seismic hazard estimation, not ML.

### `backend/algorithms/earthquake/damage.py`
Purpose:
- Converts earthquake PGA into zone and infrastructure damage states.

Class:
- `SeismicDamageEngine`

Inputs:
- `zone_data: dict`
- `infrastructure_data: list[dict]`
- `pga_map: dict[str, float]`

Outputs:
- `calculate_structural_damage(...) -> dict`

Math / logic:
- Uses fragility thresholds for damage states.
- Damage states:
  - none
  - slight
  - moderate
  - extensive
  - complete
- Uses lognormal CDF-like logic for cumulative fragility curves.
- Zone collapse ratio is computed from `complete + 0.5 * extensive`.
- Infrastructure integrity is reduced by weighted damage probabilities.

Notes:
- This is a probabilistic structural damage model, not a classifier.

### `backend/algorithms/earthquake/__init__.py`
- Docstring only.

Current state:
- Earthquake algorithms are implemented at the intensity and damage level.
- The package still lacks an orchestration layer that connects these models to calamity management and the broader simulation loop.

---

## 4.7 backend/algorithms/intervention

### `backend/algorithms/intervention/risk_assessment.py`
Purpose:
- Computes a composite risk score from casualties, infrastructure failure, flooding, and congestion.

Class:
- `RiskAssessmentEngine`

Inputs:
- `simulation_state: dict`
- `base_total_population: int`

Outputs:
- `evaluate_risk(...) -> dict`

Math / logic:
- Casualty score normalizes weighted fatalities and injuries against population.
- Infrastructure score uses `1 - average_capacity`.
- Flood score uses peak water depth normalized to 3m.
- Congestion score uses bottleneck ratios scaled from 1.0 to 3.0.
- Composite score is weighted by:
  - casualties 0.35
  - infrastructure failure 0.25
  - flooding severity 0.20
  - crowd congestion 0.20
- Severity labels are mapped by threshold:
  - Stable
  - Moderate Strain
  - High Risk
  - Critical Emergency

Notes:
- This is a rule-based composite risk engine.

---

### `backend/algorithms/intervention/recommendations.py`
Purpose:
- Generates rule-based interventions from the risk assessment report and can mutate simulation state.

Class:
- `RecommendationEngine`

Inputs:
- `risk_assessment_report: dict`
- `simulation_environment_state: dict`
- `intervention_id: str`

Outputs:
- `generate_recommendations(...) -> list[dict]`
- `apply_intervention(...) -> dict`

Logic:
- Flood risk above 40 triggers mobile pumps.
- Congestion risk above 30 triggers rerouting.
- Infrastructure risk above 30 triggers backup generators.
- Composite risk above 60 triggers mandatory evacuation.
- Interventions mutate drainage, transit, or backup power state.

Notes:
- This is a rule-based policy layer, not ML.

### `backend/algorithms/intervention/__init__.py`
- Docstring only.

Current state:
- Intervention recommendation and risk logic now exist in this folder.
- The folder still lacks a broader optimizer/decision pipeline.

---

## 4.8 backend/data

### `backend/data/glb_zone_mapping.json`
Purpose:
- Zone topology and elevation proxy derived from the GLB city model.

Contents / schema:
- `version`
- `source`
- `method`
- `warning`
- `world_coordinate_system`
- `zones` array

Each zone contains:
- `id` (string)
- `center_world` with `x`, `z`
- `center_normalized` with `x`, `y`
- `neighbors` list

How it is used:
- Flood propagation adjacency
- Evacuation graph connectivity
- Synthetic elevation proxy in ML data generation

Important note:
- The normalized `y` value is used as elevation-like data in `dataset_generator.py`.

---

### `backend/data/population.json`
Purpose:
- Derived zone population estimates.

Contents:
- `version`
- `status`
- `source`
- `zones` array

Each zone includes:
- `zone_id` (string)
- `resident_population_estimate` (int)
- `building_component_count_proxy` (int)
- `building_footprint_proxy` (float)
- `population_weight` (float)

How it is used:
- Crowd initialization
- Panic density scaling
- Zone load weighting
- Shelter and evacuation capacity proxies

---

### `backend/data/infrastructure.json`
Purpose:
- Infrastructure nodes and dependency structure.

Each node includes:
- `id` (string)
- `name` (string)
- `type` (string)
- `zone_id` (string)
- `vulnerability_threshold` (float)
- `backup_power` (float)
- `depends_on` list of parent/weight pairs

How it is used:
- Infrastructure vulnerability simulation
- Cascading dependency propagation
- Medical system health estimation
- Panic isolation stress input

---

### `backend/data/shelters.json`
Purpose:
- Shelter locations and capacities.

Each shelter includes:
- `id` (string)
- `zone_id` (string)
- `type` (string)
- `capacity` (int)

How it is used:
- Evacuation route destination filtering
- Shelter intake in crowd simulation
- HumanAgent panic destination selection in the twin system

---

### `backend/data/raw/flood_model_training.csv`
Purpose:
- Synthetic training data for the flood impact regressor.

Columns:
- `zone_id`
- `elevation`
- `flood_exposure`
- `severity`
- `day`
- `intervention`
- `drainage_weakness`
- `infra_vuln`
- `impact_score`

How it is used:
- Training and evaluation in `backend/ml/train.py` and `backend/ml/evaluate.py`

---

### `backend/data/raw/README.md`
- Explains the raw-data folder is for original unprocessed files.

---

### `backend/data/dependencies.json`
- Empty array.
- Currently unused.

### `backend/data/disaster_parameters.json`
- Empty object.
- Currently unused.

### `backend/data/historical_events.json`
- Empty array.
- Currently unused.

### `backend/data/processed`
- Empty directory.

### `backend/data/schemas`
- Empty directory.

---

## 5) Backend orchestration and NPC system

## `backend/twin`

### `backend/twin/state.py`
Purpose:
- Authoritative in-memory world state.

Key fields:
- `entities: Dict[str, Entity]`
- `simulation_time: float`
- `current_tick: int`
- `active_calamity: Optional[CalamityType]`
- `environment: Dict[str, float]`
- `metrics: Dict[str, float]`
- `events: List[dict]`

Important methods and types:
- `add_entity(entity: Entity) -> None`
- `add_entities(entities: Iterable[Entity]) -> None`
- `remove_entity(entity_id: str) -> Entity`
- `get_entity(entity_id: str) -> Optional[Entity]`
- `require_entity(entity_id: str) -> Entity`
- `get_entities() -> List[Entity]`
- `update_entity_position(entity_id: str, position: Position) -> None`
- `set_calamity(calamity_type: Optional[CalamityType]) -> None`
- `advance_time(delta_time: float) -> None`
- `record_event(event: dict) -> None`
- `update_metric(name: str, value: float) -> None`
- `clear() -> None`

Notes:
- This is state storage only.
- It does not run simulation logic itself.

---

### `backend/twin/entity.py`
Purpose:
- Base entity in the world.

Fields:
- `id: str`
- `position: Position`

Methods:
- `set_position(position: Position) -> None`
- `get_position() -> Position`

---

### `backend/twin/twin.py`
Purpose:
- Wrapper around `WorldState`.

Methods:
- `world_state` property
- `add_entity(entity: Entity) -> None`
- `add_entities(entities: Iterable[Entity]) -> None`
- `get_entity(entity_id: str) -> Optional[Entity]`
- `remove_entity(entity_id: str) -> Entity`
- `reset() -> None`
- `entity_count() -> int`

---

### `backend/twin/manager.py`
Purpose:
- Lifecycle manager for the active digital twin.

Methods:
- `create_twin(world_state: Optional[WorldState] = None) -> DigitalTwin`
- `initialize_twin(entities: Optional[Iterable[Entity]] = None, world_state: Optional[WorldState] = None) -> DigitalTwin`
- `get_active_twin() -> DigitalTwin`
- `reset_twin() -> DigitalTwin`
- `replace_twin(world_state: WorldState) -> DigitalTwin`

Notes:
- This is orchestration only.
- No simulation math.

---

## `backend/agents`

### `backend/agents/agent.py`
Purpose:
- Defines `HumanAgent`, the NPC-like entity used in the simulation.

Inheritance:
- `HumanAgent(Entity)`

Fields:
- `state: AgentState`
- `speed: float`
- `start_position: Optional[Position]`
- `target: Optional[Facility]`
- `normal_route: List[Position]`
- `normal_behavior: Optional[NormalBehavior]`
- `panic_behavior: PanicBehavior`

Key methods:
- `__post_init__() -> None`
- `configure_normal_route(route: List[Position]) -> None`
- `enter_panic(safe_centers: List[Facility]) -> bool`
- `update(delta_time: float, safe_centers: Optional[List[Facility]] = None) -> None`

NPC / behavior logic:
- NORMAL state: follows a deterministic route.
- PANIC state: selects nearest valid safe center and moves there.
- SAFE state: stops moving.

Math / logic:
- Movement itself is delegated to behavior objects and movement utilities.
- The state machine is deterministic, not ML-driven.

---

### `backend/agents/manager.py`
Purpose:
- Manages agents stored in `WorldState`.

Methods:
- `add_agent(agent: HumanAgent) -> None`
- `add_agents(agents: Iterable[HumanAgent]) -> None`
- `get_agent(agent_id: str) -> Optional[HumanAgent]`
- `get_agents() -> List[HumanAgent]`
- `get_agents_by_state(state: AgentState) -> List[HumanAgent]`
- `get_normal_agents() -> List[HumanAgent]`
- `get_panicked_agents() -> List[HumanAgent]`
- `get_safe_agents() -> List[HumanAgent]`
- `trigger_panic(agent_id: str, safe_centers) -> bool`
- `trigger_panic_for_all(safe_centers) -> int`
- `update_all(delta_time: float, safe_centers=None) -> None`

Notes:
- This is the NPC management layer.
- It does not compute flood, panic, or casualties directly.

---

### `backend/agents/movement.py`
Purpose:
- Low-level geometric movement helpers.

Functions:
- `distance(first: Position, second: Position) -> float`
- `direction(start: Position, target: Position) -> Position`
- `move_toward(current: Position, target: Position, speed: float, delta_time: float) -> Position`
- `reached(current: Position, target: Position, threshold: float = 0.1) -> bool`

Math:
- Euclidean distance in 3D.
- Direction vector normalization.
- Movement interpolation with no overshoot.

Input / output types:
- Inputs: `Position`, `float`
- Outputs: `float` or `Position`

---

### `backend/agents/normal_behavior.py`
Purpose:
- Deterministic normal movement for agents.

Class:
- `NormalBehavior`

Methods:
- `__init__(route: List[Position], speed: float = 1.0) -> None`
- `current_target` property -> `Position`
- `update(position: Position, delta_time: float) -> Position`
- `is_applicable(state: AgentState) -> bool`

Logic:
- Moves along a cyclic route.
- Uses `move_toward`.
- Advances target index when reached.

---

### `backend/agents/panic_behavior.py`
Purpose:
- Evacuation behavior for panicked agents.

Class:
- `PanicBehavior`

Methods:
- `__init__(speed: float = 2.0, arrival_threshold: float = 0.5) -> None`
- `select_safe_center(position: Position, facilities: Iterable[Facility]) -> Optional[Facility]`
- `update(position: Position, target: Facility, delta_time: float) -> Position`
- `has_reached_target(position: Position, target: Facility) -> bool`
- `is_applicable(state: AgentState) -> bool`

Logic:
- Selects nearest facility that is safe, operational, and has capacity.
- Uses Euclidean distance.
- Moves toward the target faster than normal behavior.

---

## `backend/calamities`

### `backend/calamities/base.py`
- Empty whitespace only.

### `backend/calamities/flood.py`
- Empty whitespace only.

### `backend/calamities/earthquake.py`
- Empty whitespace only.

### `backend/calamities/tsunami.py`
- Empty whitespace only.

### `backend/calamities/__init__.py`
- Docstring only.

Current state:
- The calamity classes are not yet implemented.
- The main usable calamity logic is currently in the algorithm modules, not here.

---

## `backend/decision`

### `backend/decision/response.py`
- Empty whitespace only.

### `backend/decision/recommendation.py`
- Empty whitespace only.

### `backend/decision/priority.py`
- Empty whitespace only.

### `backend/decision/optimizer.py`
- Empty.

### `backend/decision/intervention.py`
- Empty.

### `backend/decision/__init__.py`
- Not used meaningfully yet.

Current state:
- The intervention / recommendation / optimization layer is not implemented.
- This means the system can compute hazards and effects, but it cannot yet generate meaningful decision recommendations from them.

---

## `backend/api`

### `backend/api/serializers.py`
- Whitespace only.

### `backend/api/views.py`
- Whitespace only.

### `backend/api/urls.py`
- Whitespace only.

### `backend/api/apps.py`
- App definition only.

### `backend/api/__init__.py`
- Empty.

Current state:
- No API endpoints are wired.
- No serializer layer exists yet.
- No request/response contract is implemented.

---

## 6) How the whole system should function conceptually

### Flood simulation loop
1. Load zone, population, and infrastructure data.
2. Simulate water spread and water levels.
3. Convert water into per-zone flood impact.
4. Degrade infrastructure using impact and dependencies.
5. Update panic using hazard and isolation stress.
6. Compute evacuation paths.
7. Move people.
8. Update bottlenecks.
9. Estimate casualties.
10. Generate intervention recommendations.

### Earthquake simulation loop
1. Determine earthquake intensity per zone.
2. Convert intensity to building/infrastructure damage.
3. Update infrastructure and panic.
4. Update evacuation and casualties.
5. Produce intervention recommendations.

### Current gap
- The flood loop is partially real.
- The earthquake loop is not yet implemented.
- Recommendation and API loops are not yet implemented.

---

## 7) Backend data flow and wiring requirements

To make the backend functional, it needs a single orchestration path that passes state between modules.

### Expected data handoff chain
- Static data:
  - zone map
  - population
  - infrastructure
  - shelters
- Simulation state:
  - flood state per zone
  - infra state per node
  - panic per zone
  - crowd movement and bottlenecks
  - casualty totals
  - intervention state
- API should:
  - accept simulation commands
  - return current state snapshots
  - return per-zone metrics and recommendations

### Missing today
- No actual API plumbing.
- No serialization layer.
- No backend endpoint orchestration.
- No persistence layer.

---

## 8) Major bugs, risks, and unexplained behavior

### Critical bug 1: ML feature mismatch
There are two incompatible feature schemas:
- Training / evaluation schema in `backend/ml/train.py` and `backend/ml/evaluate.py`
  - `elevation`, `flood_exposure`, `severity`, `day`, `intervention`, `drainage_weakness`, `infra_vuln`
- Runtime / example schema in `backend/ml/predict.py` and `backend/algorithms/flood/impact.py`
  - `flood_exposure`, `population_density`, `drainage_weakness`, `infra_vulnerability`, `rainfall_severity`, `duration_factor`, `intervention_level`

Impact:
- Predictions may fail or be invalid.
- Model input columns do not align.
- This is the highest priority bug.

### Critical bug 2: Earthquake pipeline absent
- Earthquake code is mostly empty.
- Any feature depending on earthquake simulation will fail or remain no-op.

### Critical bug 3: API layer absent
- No working endpoints or serializers.
- Nothing exposes simulation state through HTTP yet.

### Critical bug 4: Recommendation / intervention layer absent
- Decision modules are empty.
- The system can compute risk but cannot decide what to do with it.

### Critical bug 5: Backend orchestration is not centralized
- There is no single controller that sequences flood, panic, evacuation, infrastructure, casualties, and intervention.
- This can cause state ordering bugs and inconsistent results.

### Critical bug 6: Path handling risk in ML runtime
- Some model loaders use relative paths.
- They may break depending on current working directory.

### Risk 7: Overlapping flood models
- `water_model.py` and `propagation.py` are two different flood engines.
- If both are used, results may diverge and become hard to interpret.

### Risk 8: Hidden state coupling
- Crowd, panic, casualty, and infrastructure engines all depend on each other.
- Without a strict execution order, outputs can become inconsistent.

### Risk 9: NPC / human agent model is simplistic
- HumanAgent behavior is deterministic and rule-based.
- It does not simulate heterogeneous decision-making or learning.

### Risk 10: World state tick logic is coarse
- `advance_time` increments tick by 1 regardless of delta time.
- That may not match real simulation rate semantics.

### Risk 11: Empty placeholder data files
- `dependencies.json`, `disaster_parameters.json`, `historical_events.json` are empty.
- Any logic expecting them will have no useful data.

### Risk 12: Potential capacity logic inconsistencies
- Some code uses backup power as a lower bound.
- Some code uses it as a direct fallback.
- That can create non-obvious behavior across infrastructure modules.

---

## 9) Bottom line

### What works now
- Synthetic flood dataset generation
- Flood ML training and evaluation
- Flood impact prediction logic, with schema caveats
- Flood water simulation
- Infrastructure cascade simulation
- Evacuation pathfinding
- Crowd movement and shelter intake
- Panic state updates
- Casualty estimation
- Digital twin / agent state management

### What is missing or stubbed
- Earthquake model
- Tsunami model
- Intervention recommendation engine
- API endpoints
- Serializer contracts
- Central orchestrator
- Persistence and runtime service layer

### Most important engineering fix
Unify the flood ML feature schema across:
- dataset generation
- training
- evaluation
- runtime prediction
- impact engine

Without that, the ML part is not reliable.
