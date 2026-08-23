from typing import Iterable, List, Optional

from core.enums import AgentState
from twin.state import WorldState

from agents.agent import HumanAgent


class AgentManager:
    """
    Manages human agents stored in the authoritative WorldState.
    """

    def __init__(self, world_state: WorldState) -> None:
        self.world_state = world_state

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def add_agent(self, agent: HumanAgent) -> None:
        """
        Add a human agent to the Digital Twin.
        """
        self.world_state.add_entity(agent)

    def add_agents(
        self,
        agents: Iterable[HumanAgent],
    ) -> None:
        """
        Add multiple human agents to the Digital Twin.
        """
        for agent in agents:
            self.add_agent(agent)

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    def get_agent(
        self,
        agent_id: str,
    ) -> Optional[HumanAgent]:
        """
        Retrieve a human agent by ID.
        """
        entity = self.world_state.get_entity(agent_id)

        if entity is None:
            return None

        if not isinstance(entity, HumanAgent):
            raise TypeError(
                f"Entity '{agent_id}' is not a HumanAgent."
            )

        return entity

    def get_agents(self) -> List[HumanAgent]:
        """
        Return all human agents currently in the Digital Twin.
        """
        return [
            entity
            for entity in self.world_state.get_entities()
            if isinstance(entity, HumanAgent)
        ]

    # -------------------------------------------------------------------------
    # State queries
    # -------------------------------------------------------------------------

    def get_agents_by_state(
        self,
        state: AgentState,
    ) -> List[HumanAgent]:
        """
        Return agents currently in the specified state.
        """
        return [
            agent
            for agent in self.get_agents()
            if agent.state == state
        ]

    def get_normal_agents(self) -> List[HumanAgent]:
        return self.get_agents_by_state(AgentState.NORMAL)

    def get_panicked_agents(self) -> List[HumanAgent]:
        return self.get_agents_by_state(AgentState.PANIC)

    def get_safe_agents(self) -> List[HumanAgent]:
        return self.get_agents_by_state(AgentState.SAFE)

    # -------------------------------------------------------------------------
    # State transitions
    # -------------------------------------------------------------------------

    def trigger_panic(
        self,
        agent_id: str,
        safe_centers,
    ) -> bool:
        """
        Trigger panic for a specific agent.

        Returns True if the transition succeeds.
        """
        agent = self.get_agent(agent_id)

        if agent is None:
            raise KeyError(
                f"Agent '{agent_id}' does not exist."
            )

        return agent.enter_panic(safe_centers)

    def trigger_panic_for_all(
        self,
        safe_centers,
    ) -> int:
        """
        Trigger panic for all agents that can successfully evacuate.

        Returns the number of agents transitioned to PANIC.
        """
        transitioned = 0

        for agent in self.get_normal_agents():
            if agent.enter_panic(safe_centers):
                transitioned += 1

        return transitioned

    # -------------------------------------------------------------------------
    # Simulation update
    # -------------------------------------------------------------------------

    def update_all(
        self,
        delta_time: float,
        safe_centers=None,
    ) -> None:
        """
        Advance all human agents by one simulation step.
        """
        agents = self.get_agents()

        for agent in agents:
            agent.update(
                delta_time=delta_time,
                safe_centers=safe_centers,
            )
