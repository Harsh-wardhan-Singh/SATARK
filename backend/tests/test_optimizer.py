from decision.intervention import CandidateIntervention, Intervention
from decision.optimizer import (
    OptimizationCandidateResult,
    OptimizationEngine,
    OptimizationResult,
    SimulationEvaluation,
)


def test_simulation_evaluation_dataclass():
    eval_obj = SimulationEvaluation(
        metrics={"fatalities": 2.0, "total_cost": 15000.0},
        final_risk_score=0.65,
        casualties=5.0,
        infrastructure_damage=0.25,
        congestion=0.30,
        total_surcharge_m3=120.5,
        peak_water_depth_cm=45.2,
        critical_zones_count=3,
        additional_data={"tick": 10},
    )

    d = eval_obj.to_dict()
    assert d["final_risk_score"] == 0.65
    assert d["casualties"] == 5.0
    assert d["infrastructure_damage"] == 0.25
    assert d["congestion"] == 0.30
    assert d["total_surcharge_m3"] == 120.5
    assert d["peak_water_depth_cm"] == 45.2
    assert d["critical_zones_count"] == 3
    assert d["additional_data"]["tick"] == 10


def test_optimization_candidate_result():
    intervention = Intervention(
        intervention_id="PUMP_BOOST_Z07",
        name="Deploy Mobile Pump to Zone 7",
        description="Deploy pumps to lower water depth",
        priority="HIGH",
        target="Z07",
    )
    baseline = SimulationEvaluation(
        metrics={},
        final_risk_score=0.80,
        casualties=10.0,
        infrastructure_damage=0.50,
        congestion=0.40,
        total_surcharge_m3=500.0,
    )
    result = SimulationEvaluation(
        metrics={},
        final_risk_score=0.50,
        casualties=4.0,
        infrastructure_damage=0.30,
        congestion=0.25,
        total_surcharge_m3=50.0,
    )

    cand_res = OptimizationCandidateResult(
        intervention=intervention,
        baseline=baseline,
        intervention_result=result,
        improvement_score=0.38,
        risk_reduction=0.30,
        casualty_reduction=6.0,
        infrastructure_improvement=0.20,
        congestion_improvement=0.15,
        surcharge_reduction=0.90,
        rationale="Mobile pump drastically lowered flood surcharge.",
    )

    d = cand_res.to_dict()
    assert d["intervention"]["intervention_id"] == "PUMP_BOOST_Z07"
    assert d["surcharge_reduction"] == 0.90
    assert d["improvement_score"] == 0.38
    assert "Mobile pump" in d["rationale"]


def test_compare_candidate_surcharge_reduction():
    intervention = Intervention(
        intervention_id="PUMP_BOOST_Z01",
        name="Deploy Pump",
        description="Deploy mobile pump",
        priority="HIGH",
        target="Z01",
    )
    baseline = SimulationEvaluation(
        metrics={},
        final_risk_score=0.60,
        casualties=5.0,
        infrastructure_damage=0.30,
        congestion=0.20,
        total_surcharge_m3=200.0,
    )

    # Candidate 1: lowers surcharge by 180 m3 (90% reduction)
    result_with_pump = SimulationEvaluation(
        metrics={},
        final_risk_score=0.50,
        casualties=4.0,
        infrastructure_damage=0.25,
        congestion=0.20,
        total_surcharge_m3=20.0,
    )

    # Candidate 2: same risk/casualty reduction, but zero surcharge reduction
    result_without_pump = SimulationEvaluation(
        metrics={},
        final_risk_score=0.50,
        casualties=4.0,
        infrastructure_damage=0.25,
        congestion=0.20,
        total_surcharge_m3=200.0,
    )

    cand1 = OptimizationEngine._compare_candidate(
        intervention=intervention,
        baseline=baseline,
        intervention_result=result_with_pump,
    )
    cand2 = OptimizationEngine._compare_candidate(
        intervention=intervention,
        baseline=baseline,
        intervention_result=result_without_pump,
    )

    assert cand1.surcharge_reduction == 0.90
    assert cand2.surcharge_reduction == 0.0
    assert cand1.improvement_score > cand2.improvement_score


def test_optimization_engine_ranking():
    intervention_a = Intervention(
        intervention_id="ACTION_A",
        name="Drainage Reinforcement",
        description="High capacity pumps",
        priority="HIGH",
    )
    intervention_b = Intervention(
        intervention_id="ACTION_B",
        name="Traffic Diversion",
        description="Reroute crowd",
        priority="MEDIUM",
    )

    baseline_eval = SimulationEvaluation(
        metrics={},
        final_risk_score=0.80,
        casualties=10.0,
        infrastructure_damage=0.40,
        congestion=0.50,
        total_surcharge_m3=300.0,
    )

    eval_a = SimulationEvaluation(
        metrics={},
        final_risk_score=0.40,
        casualties=3.0,
        infrastructure_damage=0.20,
        congestion=0.40,
        total_surcharge_m3=30.0,
    )

    eval_b = SimulationEvaluation(
        metrics={},
        final_risk_score=0.70,
        casualties=8.0,
        infrastructure_damage=0.35,
        congestion=0.20,
        total_surcharge_m3=290.0,
    )

    def mock_simulation_provider(scenario_payload):
        if scenario_payload is None:
            return baseline_eval
        interv = scenario_payload.get("intervention", {})
        action = interv.get("name")
        if "Drainage" in action:
            return eval_a
        return eval_b

    candidates = [
        CandidateIntervention(
            intervention=intervention_a,
            score=0.9,
            rationale=("High drainage surcharge",),
            applicable=True,
        ),
        CandidateIntervention(
            intervention=intervention_b,
            score=0.7,
            rationale=("Congestion relief",),
            applicable=True,
        ),
    ]

    optimizer = OptimizationEngine(simulation_provider=mock_simulation_provider)
    opt_result = optimizer.optimize(
        baseline_scenario={"scenario_id": "test_flood"},
        candidates=candidates,
    )

    assert isinstance(opt_result, OptimizationResult)
    assert opt_result.selected_intervention is not None
    assert opt_result.selected_intervention.intervention_id == "ACTION_A"
    assert len(opt_result.candidates) == 2
    assert opt_result.candidates[0].improvement_score >= opt_result.candidates[1].improvement_score


def test_empty_candidates_handling():
    baseline_eval = SimulationEvaluation(
        metrics={},
        final_risk_score=0.5,
    )

    def mock_provider(scenario_payload):
        return baseline_eval

    optimizer = OptimizationEngine(simulation_provider=mock_provider)
    result = optimizer.optimize(
        baseline_scenario={"scenario_id": "test_flood"},
        candidates=[],
    )

    assert result.selected_intervention is None
    assert "No applicable intervention candidates" in result.selection_reason
