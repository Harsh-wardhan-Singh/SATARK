# SATARK Backend Implementation Handoff

## Goal
Build a fast, believable disaster simulation for a partial Mumbai 3D map with:
- one canonical flood ML model,
- mathematical flood/earthquake/casualty/risk logic,
- NPC movement and panic behavior,
- recommendation and intervention outputs,
- a backend contract that the frontend can call without knowing internal model details.

The system should remain lightweight and use only basic map and zone metadata because the scene is a simplified Blender-derived city segment.

---

## Product vision

### What the user sees
1. A 3D city section of Mumbai.
2. Agents walking normally before disaster.
3. A disaster setup UI:
   - Flood severity: low / medium / high
   - Flood duration: 1 to 7 days
   - Earthquake magnitude
   - Government intervention level
4. Time progression:
   - 1 real second = 1 simulation hour
5. Flood animation:
   - water rises day by day
   - destroyed / degraded infrastructure markers appear
   - casualties and injuries update over time
6. Risk panel:
   - composite risk score
   - explanation of the score
7. Recommendation panel:
   - recommended interventions
   - why each intervention is suggested
8. NPC behavior:
   - normal walking pre-disaster
   - panic and shelter-seeking during disaster
   - crowding, congestion, and some casualty escalation

### Core design rule
Use math for everything except one flood impact ML model.

---

## Non-negotiable constraints

1. Keep only one flood ML model.
2. Make flood ML input/output schema canonical and identical for training and inference.
3. Use only one flood propagation engine.
4. Do not mutate world state directly from random modules; use adapters.
5. Do not introduce a second representation for zones.
6. Keep the system simple enough to finish fast.
7. Prefer deterministic formulas over more ML.

---

## Recommended architecture for the MVP

### Canonical pipeline
1. Load static zone data.
2. Initialize world state.
3. Simulate flood propagation.
4. Build canonical ML features.
5. Predict zone-level flood impact with one model.
6. Update infrastructure damage.
7. Update panic.
8. Compute evacuation routes.
9. Move crowd/NPCs.
10. Estimate casualties.
11. Compute risk score.
12. Generate recommendations.
13. Apply intervention effects.
14. Repeat each simulation tick.

### Earthquake path
1. Input magnitude and depth.
2. Compute PGA per zone.
3. Convert PGA to structural damage.
4. Derive infrastructure degradation and panic response.
5. Reuse evacuation/casualty/risk/recommendation layers.

---

## Canonical flood ML model

### Keep this as the single ML model
A regression model that predicts flood impact score in the range [0, 1].

### Keep the existing training target
The current synthetic target is fine for MVP if the runtime schema is fixed.

### Canonical feature schema
The model should always use these seven fields in this exact order:
1. `elevation` float
2. `flood_exposure` float
3. `severity` int
4. `day` int
5. `intervention` float
6. `drainage_weakness` float
7. `infra_vuln` float

### Feature meaning
- `elevation`: normalized zone elevation proxy from zone map
- `flood_exposure`: normalized water exposure in the current tick
- `severity`: 1, 2, or 3 for low, medium, high
- `day`: 1 to 7
- `intervention`: 0.0 to 1.0 government intervention strength
- `drainage_weakness`: 0.0 to 1.0, higher means poorer drainage
- `infra_vuln`: 0.0 to 1.0, higher means more infrastructure vulnerability

### Fix required
Training and inference must build exactly the same columns.

### Feature contract strategy
Create one shared feature builder in `backend/ml/features.py` and use it everywhere:
- training
- evaluation
- predictor
- flood impact engine

### Model type
Keep the current regression approach:
- `RandomForestRegressor` is acceptable for speed.
- No classification model is needed here.

### Why regression, not classification
Because the system needs a continuous impact score that later drives:
- damage probability
- risk scoring
- recommendations
- casualty growth

---

## Canonical flood propagation model

### Use only one of the two existing engines
Recommended MVP choice: `backend/algorithms/flood/propagation.py`

### Why this one
- It is easier to use with the current zone mapping JSON.
- It already uses zone neighbors and fixed drainage.
- It needs less data than `WaterModel`.
- It is simpler to wire into the rest of the backend quickly.

### What to do with `water_model.py`
- Keep it only if you want it as a reference.
- Do not call it in the runtime pipeline.
- Do not let both models run in parallel.

### Canonical flood engine output
- zone water level per tick

### Required normalization
Use the flood engine output to compute `flood_exposure` consistently, for example:
- `flood_exposure = min(1.0, water_level / max_expected_water_level)`

Keep this mapping fixed across training and runtime.

---

## Earthquake model plan

### Keep earthquake math only
Do not make earthquake ML for MVP.

### Existing math modules to use
- `backend/algorithms/earthquake/intensity.py`
- `backend/algorithms/earthquake/damage.py`

### Earthquake execution order
1. User chooses magnitude and depth.
2. `SeismicEngine.calculate_pga(...)` returns per-zone PGA.
3. `SeismicDamageEngine.calculate_structural_damage(...)` returns:
   - zone damage states
   - infrastructure damage states
4. Convert structural integrity into downstream panic and casualties.

### Earthquake output should feed
- infrastructure degradation
- evacuation path changes
- casualty estimation
- risk score
- recommendations

### No extra earthquake ML needed
This keeps the build fast.

---

## Risk system plan

### Keep the rule-based risk engine
Use `backend/algorithms/intervention/risk_assessment.py` as the risk scorer.

### Required input to risk engine
A simulation state dict with:
- casualties
- infra_status
- flood_states
- bottlenecks

### Output
- `composite_risk_score` in 0-100
- severity label
- component breakdown
- explainable summary

### Recommended UI behavior
- Show the score on the side panel.
- Expand to reveal:
  - casualties component
  - infrastructure component
  - flooding component
  - congestion component
  - explanation bullets

### Why this is enough
The risk score is not ML; it is a weighted deterministic summary of the simulation state.

---

## Recommendation system plan

### Keep the rule-based recommendation engine
Use `backend/algorithms/intervention/recommendations.py`.

### Inputs
- risk report
- simulation environment state

### Outputs
- ranked intervention list
- explanation for each intervention

### Interventions currently available
1. Mobile drainage pumps
2. Emergency traffic rerouting
3. Backup generators
4. Mandatory evacuation order

### Rule thresholds
- flood > 40 => pumps
- congestion > 30 => reroute traffic
- infrastructure > 30 => generators
- composite risk > 60 => evacuation order

### Recommended behavior
- Generate recommendations after every tick.
- Allow the frontend judge/operator to apply one intervention.
- Recompute the simulation state after intervention.

---

## NPC / human psychology system plan

### Current style
Keep NPCs deterministic and lightweight.

### Existing base pieces
- `backend/agents/agent.py`
- `backend/agents/normal_behavior.py`
- `backend/agents/panic_behavior.py`
- `backend/agents/movement.py`
- `backend/agents/manager.py`

### NPC state machine
Use three states only:
1. NORMAL
2. PANIC
3. SAFE

### NORMAL behavior
- Walk along a fixed route.
- Keep movement deterministic.

### PANIC behavior
- Select nearest valid shelter.
- Move faster than normal.
- Increase congestion and collision-like pressure.

### SAFE behavior
- Stop movement once shelter is reached.

### Realism additions to keep it simple
You do not need a full psychology ML model.
Use math-based modifiers instead:
- panic multiplier by flood severity
- panic multiplier by infrastructure failure
- congestion penalty in evacuation routes
- reduced movement speed in high panic
- small chance of stumble / delay if congestion is high

### Recommended NPC math additions
1. Panic level rises with local flood and isolation.
2. Movement speed reduces when panic exceeds a threshold.
3. Bottlenecks slow path progress.
4. Shelter capacity limits create spillover and crowding.
5. Crowding can slightly increase casualty estimates.

### Important constraint
Do not replace the HumanAgent model with a new unrelated system.
Extend the current one.

---

## Casualty model plan

### Keep it mathematical
Use `backend/algorithms/casualties/estimation.py`.

### Inputs needed
- current exposed population
- flood level
- bottlenecks
- panic
- medical system health

### Outputs
- total fatalities
- total injuries
- zone breakdown
- medical system health

### Recommended casualty sources
1. Direct flood exposure
2. Crowd crush / bottleneck effect
3. Untreated injuries due to medical failure

### If you need realism fast
Do not chase real-world precision.
Use calibrated multipliers and cap values.
That is sufficient for a judge-facing demo.

---

## Data strategy

### What you already have
- zone mapping
- population proxies
- infrastructure graph
- shelters
- synthetic flood ML data

### What you probably still need
- cleaner zone-level drainage proxy
- zone-level infrastructure vulnerability score
- zone-level population density proxy
- some historical flood calibration values
- basic earthquake fragility calibration values

### Where to get data quickly
Because time is short, prefer these sources in order:
1. Existing project JSON files
2. Synthetic calibration from your current city map
3. Public historic event summaries
4. Open city or disaster datasets if easy to integrate

### What not to do now
- Do not spend time trying to build a giant official data lake.
- Do not block the MVP on perfect government data.
- Do not overfit the model to unavailable real-world sources.

### Good enough data sources for MVP
- existing zone geometry from Blender-derived map
- existing population estimates
- existing infrastructure JSON
- synthetic training samples from formula generation
- manually assigned fragility and drainage parameters

---

## Backend contract plan

### Need a single simulation API boundary
The backend should expose structured data and not expose internal sklearn or simulation details.

### Suggested endpoints or internal service methods
- initialize simulation
- step simulation tick
- apply disaster configuration
- apply intervention
- get current state
- get risk report
- get recommendation report
- get NPC / shelter status

### State to return to frontend
- zone water levels
- flood impact score by zone
- infrastructure statuses
- casualty totals
- panic levels
- NPC state summary
- bottlenecks
- evacuation routes
- risk breakdown
- recommendations

### Input from frontend
- disaster type
- severity or magnitude
- days or duration
- intervention level
- time step controls
- optional manual interventions

### Important design rule
Use a clean adapter layer between backend math and frontend JSON.

---

## Required file-level work plan

### ML package
1. Implement `backend/ml/features.py` as canonical feature builder.
2. Update `backend/ml/dataset_generator.py` to use it.
3. Update `backend/ml/train.py` to use it.
4. Update `backend/ml/evaluate.py` to use it.
5. Update `backend/ml/predict.py` to use it.
6. Update `backend/algorithms/flood/impact.py` to use it.
7. Validate model artifact path handling.
8. Add basic ML tests.

### Flood algorithms
1. Pick `propagation.py` as canonical flood engine.
2. Build a simple adapter for it.
3. Feed its output into flood impact.
4. Retire `water_model.py` from runtime use.

### Earthquake algorithms
1. Keep intensity and damage models.
2. Connect them into the disaster pipeline.
3. Feed outputs into risk, evacuation, and casualty layers.

### Intervention system
1. Keep risk assessment.
2. Keep recommendations.
3. Add a small state adapter so interventions can modify flood and infrastructure variables safely.

### NPC system
1. Preserve `HumanAgent`.
2. Keep route-based movement.
3. Add simple congestion and panic modifiers.
4. Integrate shelters and panic transition.

### Backend orchestration
1. Create a simulation coordinator.
2. Centralize tick order.
3. Return structured JSON to frontend.
4. Add API wiring later if needed.

---

## Suggested tick order

This is the order every simulation step should follow:
1. Receive current scenario settings.
2. Advance flood / earthquake hazard state.
3. Build ML flood features.
4. Predict impact.
5. Update infrastructure.
6. Update panic.
7. Recompute evacuation routes.
8. Move NPCs.
9. Update crowd congestion.
10. Estimate casualties.
11. Compute risk.
12. Compute recommendations.
13. Apply intervention if selected.
14. Emit snapshot to frontend.

---

## What to tell the backend engineer right now

### Primary goal
Make the simulation work end-to-end with one flood ML model and math-based everything else.

### Priority 1
Fix the flood ML feature mismatch.

### Priority 2
Choose one flood propagation model and use only that one.

### Priority 3
Wire earthquake intensity and damage into the same state pipeline.

### Priority 4
Expose risk and recommendations in structured output.

### Priority 5
Keep NPC behavior simple but believable.

---

## Handoff for another agent

### Mission statement
Build a fast, lightweight disaster simulator for a partial Mumbai 3D map using one flood ML model and deterministic math for the rest.

### Required deliverables
1. Canonical ML feature contract.
2. Single flood propagation adapter.
3. Earthquake pipeline integration.
4. Risk and recommendation output pipeline.
5. NPC movement and panic integration.
6. Structured backend snapshot contract.

### Must not do
- Do not create a second ML flood model.
- Do not keep two flood engines in runtime.
- Do not replace the current agent model.
- Do not overcomplicate with unnecessary ML.

### Acceptance criteria
- Training and inference use identical features.
- Flood simulation can run for 1 to 7 days.
- Earthquake can be configured by magnitude and intervention level.
- Risk and recommendations are visible and explainable.
- NPCs move, panic, and shelter-seek.
- Backend returns structured state for frontend use.

---

## Suggested first implementation order

1. Fix `features.py` and the flood schema mismatch.
2. Choose one flood engine.
3. Add a small simulation coordinator.
4. Connect flood impact, infra, panic, evac, crowd, casualties.
5. Connect risk and recommendations.
6. Add earthquake path.
7. Add API response shape.
8. Add tests.

---

## Short answer on feasibility
Yes, the idea is good and feasible for a fast judge-facing MVP if you keep the system simple:
- one flood ML model only
- math for everything else
- one flood engine
- deterministic risk/recommendation rules
- lightweight NPC behavior

That is the fastest path to something intelligent and demonstrable.
