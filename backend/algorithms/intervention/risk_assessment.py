class RiskAssessmentEngine:
    def __init__(self, weights=None):
        # Weights for the composite risk score calculation
        self.weights = weights or {
            "casualties": 0.35,
            "infrastructure_failure": 0.25,
            "flooding_severity": 0.20,
            "crowd_congestion": 0.20
        }

    def evaluate_risk(self, simulation_state, base_total_population):
        """
        Computes a composite risk score (0-100) and generates an explainable breakdown.
        
        simulation_state expects:
        - casualties: {"total_fatalities": int, "total_injuries": int, ...}
        - infra_status: dict of infrastructure node capacities
        - flood_states: dict of zone water depths
        - bottlenecks: dict of zone congestion ratios
        """
        # 1. Component A: Casualty Impact (Normalized against total population)
        cas = simulation_state.get("casualties", {"total_fatalities": 0, "total_injuries": 0})
        total_cas = cas["total_fatalities"] * 3.0 + cas["total_injuries"] * 1.0 # Fatalities weigh heavier
        cas_score = min(100.0, (total_cas / max(base_total_population, 1)) * 200.0)

        # 2. Component B: Infrastructure Failure (Average offline/degraded percentage)
        infra = simulation_state.get("infra_status", {})
        if infra:
            total_capacity = sum(node["capacity"] for node in infra.values())
            avg_capacity = total_capacity / len(infra)
            infra_fail_score = (1.0 - avg_capacity) * 100.0
        else:
            infra_fail_score = 0.0

        # 3. Component C: Flooding Severity (Average water depth normalized to 3m max)
        floods = simulation_state.get("flood_states", {})
        if floods:
            max_flood = max(floods.values()) if floods else 0.0
            flood_score = min(100.0, (max_flood / 3.0) * 100.0)
        else:
            flood_score = 0.0

        # 4. Component D: Crowd Congestion / Bottlenecks
        bottlenecks = simulation_state.get("bottlenecks", {})
        if bottlenecks:
            max_bottleneck = max(bottlenecks.values()) if bottlenecks else 1.0
            # A ratio above 1.0 indicates overcrowding. Scale 1.0-3.0 to 0-100
            congestion_score = min(100.0, max(0.0, (max_bottleneck - 1.0) / 2.0) * 100.0)
        else:
            congestion_score = 0.0

        # Compute Final Composite Score
        composite_score = (
            (cas_score * self.weights["casualties"]) +
            (infra_fail_score * self.weights["infrastructure_failure"]) +
            (flood_score * self.weights["flooding_severity"]) +
            (congestion_score * self.weights["crowd_congestion"])
        )

        # Generate Explainable Summary (The "Why")
        drivers = []
        if flood_score > 50:
            drivers.append(f"Severe flooding detected with peak depths reaching hazardous levels.")
        if infra_fail_score > 40:
            drivers.append(f"Critical infrastructure grid degradation is impacting emergency response and medical triage.")
        if congestion_score > 30:
            drivers.append(f"Major transit bottlenecks are trapping crowds in high-risk zones.")
        if cas_score > 25:
            drivers.append(f"Casualty numbers are rising due to environmental exposure and system strain.")
        
        if not drivers:
            drivers.append("The situation is currently stable with minimal systemic disruption.")

        return {
            "composite_risk_score": round(composite_score, 1),
            "severity_label": self._get_severity_label(composite_score),
            "breakdown": {
                "casualties": round(cas_score, 1),
                "infrastructure": round(infra_fail_score, 1),
                "flooding": round(flood_score, 1),
                "congestion": round(congestion_score, 1)
            },
            "explainable_summary": drivers
        }

    def _get_severity_label(self, score):
        if score >= 75: return "CRITICAL EMERGENCY"
        if score >= 50: return "HIGH RISK"
        if score >= 25: return "MODERATE STRAIN"
        return "STABLE"