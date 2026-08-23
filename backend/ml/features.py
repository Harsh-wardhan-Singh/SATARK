from dataclasses import dataclass
from typing import Mapping

class StateFeatureExtractor:
    def __init__(self, zone_ids, infra_ids):
        """
        Initializes the extractor with a fixed order of zones and infrastructure.
        The order must remain constant so the ML model always receives 
        the same feature at the same array index.
        """
        self.zone_ids = sorted(zone_ids)
        self.infra_ids = sorted(infra_ids)
        
        # Calculate expected vector size for validation
        # Per Zone: [water_level, bottleneck, panic_level, casualty_ratio]
        # Per Infra: [operational_capacity]
        self.vector_size = (len(self.zone_ids) * 4) + len(self.infra_ids)

    def extract_features(self, flood_states, bottlenecks, panic_states, casualties_data, infra_states, base_populations):
        """
        Flattens the entire multi-dimensional simulation state into a single 
        normalized 1D list (vector) for ML model consumption.
        """
        feature_vector = []

        # 1. Zone-Level Features (4 features per zone)
        for zone in self.zone_ids:
            # Feature A: Water Level (Normalized to assumed max depth of 5.0m)
            water_depth = flood_states.get(zone, 0.0)
            feature_vector.append(min(water_depth / 5.0, 1.0))
            
            # Feature B: Bottleneck Severity (Normalized to assumed max of 3.0 ratio)
            congestion = bottlenecks.get(zone, 0.0)
            feature_vector.append(min(congestion / 3.0, 1.0))
            
            # Feature C: Panic State (Already 0.0 to 1.0)
            panic = panic_states.get(zone, 0.0)
            feature_vector.append(panic)
            
            # Feature D: Casualty Ratio (Injuries + Fatalities / Base Population)
            zone_cas = casualties_data.get(zone, {"fatalities": 0, "injuries": 0})
            total_cas = zone_cas["fatalities"] + zone_cas["injuries"]
            base_pop = base_populations.get(zone, 1) # Avoid division by zero
            feature_vector.append(min(total_cas / base_pop, 1.0))

        # 2. Infrastructure-Level Features (1 feature per node)
        for infra in self.infra_ids:
            # Feature E: Operational Capacity (Already 0.0 to 1.0)
            state = infra_states.get(infra, {'capacity': 1.0})
            # Handle both raw float states and dictionary states depending on the engine's exact output
            capacity = state['capacity'] if isinstance(state, dict) else state
            feature_vector.append(capacity)

        # 3. Validation
        if len(feature_vector) != self.vector_size:
            raise ValueError(f"Feature vector shape mismatch. Expected {self.vector_size}, got {len(feature_vector)}")

        return feature_vector

FEATURE_NAMES = (
    "elevation",
    "flood_exposure",
    "severity",
    "day",
    "intervention",
    "drainage_weakness",
    "infra_vuln",
)


@dataclass(frozen=True)
class FloodImpactFeatures:
    """
    Canonical feature contract for the SATARK flood-impact model.

    IMPORTANT:
    The order of these fields must remain identical to FEATURE_NAMES
    because the trained Random Forest model was trained using this schema.
    """

    elevation: float
    flood_exposure: float
    severity: int
    day: int
    intervention: float
    drainage_weakness: float
    infra_vuln: float

    def as_dict(self) -> dict[str, float | int]:
        """
        Return features using the canonical model column names.
        """
        return {
            "elevation": self.elevation,
            "flood_exposure": self.flood_exposure,
            "severity": self.severity,
            "day": self.day,
            "intervention": self.intervention,
            "drainage_weakness": self.drainage_weakness,
            "infra_vuln": self.infra_vuln,
        }

    def as_ordered_list(self) -> list[float | int]:
        """
        Return the feature vector in the exact training order.
        """
        return [
            self.elevation,
            self.flood_exposure,
            self.severity,
            self.day,
            self.intervention,
            self.drainage_weakness,
            self.infra_vuln,
        ]


class FloodFeatureBuilder:
    """
    Constructs canonical flood-impact features from simulation inputs.

    This class contains feature engineering only.

    It does not:
        - load the ML model
        - call sklearn
        - perform prediction
        - modify WorldState
    """

    @staticmethod
    def build(
        *,
        elevation: float,
        flood_exposure: float,
        severity: int,
        day: int,
        intervention: float,
        drainage_weakness: float,
        infra_vuln: float,
    ) -> FloodImpactFeatures:
        """
        Construct and validate the canonical flood feature set.
        """
        elevation = float(elevation)
        flood_exposure = float(flood_exposure)
        severity = int(severity)
        day = int(day)
        intervention = float(intervention)
        drainage_weakness = float(drainage_weakness)
        infra_vuln = float(infra_vuln)

        if not 0.0 <= elevation <= 1.0:
            raise ValueError(
                "elevation must be within [0.0, 1.0]."
            )

        if not 0.0 <= flood_exposure <= 1.0:
            raise ValueError(
                "flood_exposure must be within [0.0, 1.0]."
            )

        if severity not in (1, 2, 3):
            raise ValueError(
                "severity must be one of 1, 2, or 3."
            )

        if not 1 <= day <= 7:
            raise ValueError(
                "day must be within [1, 7]."
            )

        for name, value in (
            ("intervention", intervention),
            ("drainage_weakness", drainage_weakness),
            ("infra_vuln", infra_vuln),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be within [0.0, 1.0]."
                )

        return FloodImpactFeatures(
            elevation=elevation,
            flood_exposure=flood_exposure,
            severity=severity,
            day=day,
            intervention=intervention,
            drainage_weakness=drainage_weakness,
            infra_vuln=infra_vuln,
        )

    @staticmethod
    def from_mapping(
        features: Mapping[str, float | int],
    ) -> FloodImpactFeatures:
        """
        Construct canonical features from a mapping.

        Rejects missing or unexpected fields so incompatible runtime
        schemas cannot silently reach the model.
        """
        expected = set(FEATURE_NAMES)
        received = set(features.keys())

        missing = expected - received
        unexpected = received - expected

        if missing:
            raise ValueError(
                "Missing flood-impact features: "
                + ", ".join(sorted(missing))
            )

        if unexpected:
            raise ValueError(
                "Unexpected flood-impact features: "
                + ", ".join(sorted(unexpected))
            )

        return FloodFeatureBuilder.build(
            elevation=features["elevation"],
            flood_exposure=features["flood_exposure"],
            severity=features["severity"],
            day=features["day"],
            intervention=features["intervention"],
            drainage_weakness=features["drainage_weakness"],
            infra_vuln=features["infra_vuln"],
        )