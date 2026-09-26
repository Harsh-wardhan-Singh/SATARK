import re
from pathlib import Path

engine_file = Path(r"c:\Users\sitak\SATARK\backend\simulation\engine.py")
code = engine_file.read_text(encoding="utf-8")

# Check methods that were part of the old monolithic stepping
legacy_monolith_candidates = [
    "_step_flood",
    "_step_impact",
    "_step_infrastructure",
    "_step_casualties",
    "_step_human_response",
    "_step_risk",
    "_step_decision",
    "_step_metrics",
    "_calculate_infrastructure_damage",
    "_calculate_congestion",
    "_build_simulation_evaluation",
    "_provide_simulation_evaluation",
    "_clone_scenario_with_intervention",
    "_clone_initial_entities",
    "_apply_scenario_intervention",
    "_build_intervention_environment",
    "_merge_intervention_environment",
    "apply_selected_intervention",
    "apply_recommendation",
    "get_intervention_state",
    "clear_intervention",
    "run_until_complete",
    "is_finished",
]

print("Checking presence of candidate methods:")
for m in legacy_monolith_candidates:
    has_def = f"def {m}(" in code
    calls = len(re.findall(r"\b" + m + r"\b", code))
    print(f"  {m:35s}: defined={has_def}, occurrences={calls}")
