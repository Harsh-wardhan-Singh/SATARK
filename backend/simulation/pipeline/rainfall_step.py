from __future__ import annotations

from simulation.pipeline.base_step import SimulationStep, StepContext


class RainfallStep(SimulationStep):
    """
    Applies current scenario rainfall intensity to the environment,
    evaluating dynamic hyetographs when configured.
    """

    @property
    def name(self) -> str:
        return "RainfallStep"

    def execute(self, context: StepContext) -> None:
        if context.hyetograph is not None:
            rainfall_intensity = context.hyetograph.get_intensity(
                context.clock.simulation_time
            )
        else:
            rainfall_intensity = context.scenario.rainfall_intensity

        context.world.state.environment["rainfall_intensity"] = rainfall_intensity
        if context.flood is not None:
            context.flood.set_rainfall(rainfall_intensity)

