# SATARK — REST API Reference & Schema Specification

> **Base URL**: `http://localhost:8000/api/`  
> **Content-Type**: `application/json`  
> **Version**: 1.0 (Phase 10 Production Protocol)

This document provides complete, authoritative specifications for all REST endpoints exposed by SATARK's Django REST Framework (DRF) backend.

---

## Table of Contents
- [1. General Conventions & Response Envelope](#1-general-conventions--response-envelope)
- [2. Simulation Lifecycle Endpoints](#2-simulation-lifecycle-endpoints)
  - [GET /api/simulation/state/](#get-apisimulationstate)
  - [POST /api/simulation/start/](#post-apisimulationstart)
  - [POST /api/simulation/step/](#post-apisimulationstep)
  - [POST /api/simulation/pause/](#post-apisimulationpause)
  - [POST /api/simulation/resume/](#post-apisimulationresume)
  - [POST /api/simulation/reset/](#post-apisimulationreset)
  - [POST /api/simulation/nowcast/](#post-apisimulationnowcast)
  - [GET /api/simulation/presets/](#get-apisimulationpresets)
- [3. World Geography & Infrastructure Endpoints](#3-world-geography--infrastructure-endpoints)
  - [GET /api/world/zones/](#get-apiworldzones)
  - [GET /api/world/safe-zones/](#get-apiworldsafe-zones)
- [4. Navigation & Evacuation Endpoints](#4-navigation--evacuation-endpoints)
  - [POST /api/navigation/route/](#post-apinavigationroute)
- [5. Decision Support & Optimization Endpoints](#5-decision-support--optimization-endpoints)
  - [POST /api/decision/interventions/](#post-apidecisioninterventions)
  - [POST /api/decision/interventions/evaluate/](#post-apidecisioninterventionsevaluate)
  - [POST /api/decision/interventions/apply/](#post-apidecisioninterventionsapply)

---

## 1. General Conventions & Response Envelope

### Standard Success Response
All successful responses return HTTP status `200 OK` (or `201 Created` for resource creation) with a structured JSON body:
```json
{
  "status": "success",
  "data": { ... }
}
```

### Standard Error Response
In case of invalid payloads or illegal state machine transitions, standard HTTP error codes (`400 Bad Request`, `404 Not Found`, `500 Internal Error`) are returned:
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_STATE",
    "message": "Simulation must be initialized before stepping.",
    "details": {}
  }
}
```

---

## 2. Simulation Lifecycle Endpoints

### `GET /api/simulation/state/`
Returns the complete authoritative Digital Twin world state at the current tick.

#### Response Schema
```json
{
  "time": 7200.0,
  "tick": 2,
  "calamity_type": "FLOOD",
  "metrics": {
    "total_fatalities": 0,
    "total_injuries": 2,
    "safe_population": 218,
    "evacuating_population": 30,
    "displaced_population": 0,
    "overall_risk_index": 0.42,
    "agent_count": 250
  },
  "environment": {
    "rainfall_intensity": 65.5,
    "flood_water_levels": {
      "Z01": 0.05,
      "Z02": 0.08,
      "Z04": 0.38,
      "Z08": 0.42
    },
    "drainage": {
      "overall_utilization": 0.88,
      "surcharged_nodes": ["J_Z04", "J_Z08"],
      "zone_drainage": {
        "Z04": {
          "pipe_utilization": 1.35,
          "is_surcharging": true,
          "capacity_cms": 1.25,
          "inflow_cms": 1.69
        }
      }
    },
    "infrastructure": {
      "E01": { "status": "FAILED", "type": "POWER_SUBSTATION", "zone_id": "Z04" },
      "W01": { "status": "DEGRADED", "type": "WATER_TREATMENT", "zone_id": "Z08" },
      "H02": { "status": "OPERATIONAL", "type": "HOSPITAL", "zone_id": "Z05" }
    }
  },
  "entities": [
    {
      "id": "agent_001",
      "type": "HUMAN",
      "position": [12.4, 0.0, 45.2],
      "zone_id": "Z04",
      "state": "PANIC",
      "speed": 8.0,
      "target_shelter_id": "SHELTER_02"
    }
  ],
  "events": [
    {
      "time": 7200.0,
      "type": "INFRASTRUCTURE_FAILURE",
      "message": "Substation E01 tripped due to flood level exceeding 30 cm."
    }
  ]
}
```

---

### `POST /api/simulation/start/`
Initializes or reconfigures a disaster simulation scenario.

#### Request Body Schema
```json
{
  "scenario_id": "mumbai_2005_cloudburst",
  "duration_seconds": 86400,
  "calamity_type": "FLOOD",
  "zone_id": "Z04",
  "severity": 3,
  "rainfall_intensity": 95.0,
  "hyetograph_type": "mumbai_2005_cloudburst",
  "representative_agent_count": 250
}
```

#### Curl Example
```bash
curl -X POST http://localhost:8000/api/simulation/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "mumbai_2005",
    "duration_seconds": 86400,
    "zone_id": "Z04",
    "severity": 3,
    "hyetograph_type": "mumbai_2005_cloudburst"
  }'
```

---

### `POST /api/simulation/step/`
Advances the authoritative simulation by exactly one tick ($\Delta t = 3600\text{ s}$). Executes the full 9-step simulation pipeline.

#### Request Body
Empty JSON `{}`.

#### Response
Returns the updated `WorldState` JSON object identical to `GET /api/simulation/state/`. Execution latency: $\sim 12\text{ ms}$.

---

### `POST /api/simulation/pause/`
Pauses the active stepping cycle.

### `POST /api/simulation/resume/`
Resumes a paused simulation.

### `POST /api/simulation/reset/`
Resets the Digital Twin to initial t=0 condition. Clears all flood heights, resets infrastructure status to healthy, and returns agents to their home zones.

---

### `POST /api/simulation/nowcast/`
Forks an in-memory clone of current state and projects forward flood depths without mutating the live baseline run.

#### Request Body Schema
```json
{
  "horizon_hours": [1.0, 2.0, 3.0]
}
```

#### Response Schema
```json
{
  "status": "success",
  "horizons": [
    {
      "horizon_hours": 1.0,
      "projected_time": 10800.0,
      "water_depth_cm": {
        "Z01": 5.2,
        "Z04": 38.4,
        "Z08": 42.1
      },
      "critical_zones_count": 2
    },
    {
      "horizon_hours": 2.0,
      "projected_time": 14400.0,
      "water_depth_cm": {
        "Z01": 8.0,
        "Z04": 49.6,
        "Z08": 54.0
      },
      "critical_zones_count": 4
    }
  ]
}
```

---

### `GET /api/simulation/presets/`
Returns the standardized disaster scenario presets configured for one-click operator drills.

#### Response Schema
```json
{
  "presets": [
    {
      "id": "standard_monsoon",
      "name": "Standard Monsoon Inundation",
      "description": "Continuous seasonal rainfall (35 mm/hr) over 24 hours.",
      "duration": 86400,
      "severity": 1,
      "target_zone": "Z04",
      "hyetograph_type": "uniform",
      "rainfall_intensity": 35.0
    },
    {
      "id": "severe_flash_flood",
      "name": "Severe Flash Flood",
      "description": "Intense localized cloudburst (75 mm/hr) over 12 hours.",
      "duration": 43200,
      "severity": 2,
      "target_zone": "Z08",
      "hyetograph_type": "huff_q2",
      "rainfall_intensity": 75.0
    },
    {
      "id": "mumbai_2005_cloudburst",
      "name": "Mumbai 2005 Benchmark Cloudburst",
      "description": "Historical 944 mm 24-hour extreme precipitation benchmark.",
      "duration": 86400,
      "severity": 3,
      "target_zone": "Z04",
      "hyetograph_type": "mumbai_2005_cloudburst",
      "rainfall_intensity": 190.3
    }
  ]
}
```

---

## 3. World Geography & Infrastructure Endpoints

### `GET /api/world/zones/`
Returns spatial, topographic, and municipal ward definitions for all 21 zones (`Z01` through `Z21`).

#### Response Schema
```json
{
  "zones": [
    {
      "id": "Z04",
      "name": "Ward F/North - Dadar / Matunga",
      "ward_code": "F/N",
      "ward_name": "F/North (Dadar/Matunga)",
      "risk_classification": "High Density / Coastal Lowland",
      "primary_land_use": "Mixed Commercial / Residential",
      "elevation": 4.2,
      "area_m2": 150000.0,
      "drainage_density": 1.25,
      "center_normalized": { "x": 0.42, "y": 0.58 },
      "polygon": [
        [19.018, 72.842],
        [19.025, 72.848],
        [19.021, 72.855]
      ]
    }
  ]
}
```

---

### `GET /api/world/safe-zones/`
Returns the authoritative, backend-designated emergency evacuation shelters.

#### Response Schema
```json
{
  "safe_zones": [
    {
      "zoneId": "Z05",
      "name": "Worli Municipal Sports Complex",
      "shelter_id": "SHELTER_01",
      "capacity": 500,
      "current_occupancy": 142,
      "elevation": 18.5,
      "status": "OPEN",
      "coordinates": { "lat": 19.008, "lng": 72.818 }
    }
  ]
}
```

---

## 4. Navigation & Evacuation Endpoints

### `POST /api/navigation/route/`
Computes an optimal flood-safe evacuation route from origin to destination across the city road graph.

#### Request Body Schema
```json
{
  "origin_zone": "Z04",
  "destination_zone": "Z05",
  "max_depth_threshold_cm": 30.0
}
```

#### Response Schema
```json
{
  "status": "success",
  "route": {
    "waypoints": ["Z04", "Z03", "Z05"],
    "total_distance_km": 3.8,
    "max_flood_depth_cm": 12.0,
    "is_safe": true,
    "instructions": [
      "Evacuate west along Tilak Road toward Z03",
      "Proceed south along Dr. Annie Besant Road to Shelter Z05"
    ]
  }
}
```

---

## 5. Decision Support & Optimization Endpoints

### `POST /api/decision/interventions/`
Returns rule-based emergency intervention recommendations dynamically triggered by current world state.

#### Response Schema
```json
{
  "recommendations": [
    {
      "id": "rec_pump_z04",
      "intervention_id": "deploy_mobile_pumps",
      "name": "Deploy High-Capacity Mobile Pumps",
      "description": "Deploy two 500 m³/hr diesel pumps to drain Dadar low point.",
      "target_zone": "Z04",
      "priority": "HIGH",
      "cost_estimate_inr": 250000,
      "rationale": "Pipe utilization in Z04 reached 135%; water height threatening Substation E01."
    }
  ]
}
```

---

### `POST /api/decision/interventions/evaluate/`
Executes parallel counterfactual simulations comparing baseline trajectory against proposed intervention candidates.

#### Request Body Schema
```json
{
  "candidate_ids": ["deploy_mobile_pumps", "dispatch_backup_power"]
}
```

#### Response Schema
```json
{
  "baseline": {
    "projected_fatalities": 4,
    "projected_injuries": 18,
    "infrastructure_failed_count": 3,
    "max_flood_volume_m3": 184000.0
  },
  "candidates": [
    {
      "intervention_id": "deploy_mobile_pumps",
      "score": 0.88,
      "projected_fatalities": 0,
      "projected_injuries": 6,
      "infrastructure_failed_count": 1,
      "delta": {
        "fatalities_avoided": 4,
        "injuries_avoided": 12,
        "infrastructure_saved": 2,
        "flood_volume_reduction_pct": 28.5
      },
      "selection_explanation": "Prevents Substation E01 trip, averting downstream water treatment blackout."
    }
  ],
  "optimal_intervention_id": "deploy_mobile_pumps"
}
```

---

### `POST /api/decision/interventions/apply/`
Authoritatively applies an approved intervention into the active Digital Twin state.

#### Request Body Schema
```json
{
  "intervention_id": "deploy_mobile_pumps",
  "target_zone": "Z04"
}
```

#### Response Schema
```json
{
  "status": "applied",
  "intervention_id": "deploy_mobile_pumps",
  "applied_at_time": 7200.0,
  "message": "Mobile pump deployed to Z04. Drainage boost of +0.05 m/hr active."
}
```
