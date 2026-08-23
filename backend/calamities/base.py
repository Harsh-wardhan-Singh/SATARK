from abc import ABC, abstractmethod
from typing import Any, Dict

from core.enums import CalamityType


class Calamity(ABC):
    """
    Base contract for SATARK calamity simulations.

    A calamity is responsible for producing hazard-specific state.

    It does not perform:
        - risk assessment
        - decision making
        - infrastructure policy
        - API handling
        - frontend rendering
        - ML feature engineering
    """

    calamity_type: CalamityType

    def __init__(
        self,
        parameters: Dict[str, Any] | None = None,
    ) -> None:
        self.parameters: Dict[str, Any] = dict(
            parameters or {}
        )

        self._initialized = False
        self._state: Dict[str, Any] = {}

    @property
    def is_initialized(self) -> bool:
        """
        Return whether this calamity has been initialized.
        """
        return self._initialized

    @property
    def state(self) -> Dict[str, Any]:
        """
        Return a copy of the current calamity state.
        """
        return dict(self._state)

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the calamity.
        """
        raise NotImplementedError

    @abstractmethod
    def step(self, delta_time: float) -> Dict[str, Any]:
        """
        Advance the calamity by one simulation step.

        Returns:
            The current hazard state.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """
        Reset the calamity to an uninitialized state.
        """
        self._initialized = False
        self._state.clear()

    def _require_initialized(self) -> None:
        """
        Ensure that the calamity has been initialized.
        """
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} "
                "has not been initialized."
            )
