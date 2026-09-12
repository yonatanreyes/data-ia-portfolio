"""Common interface every AI provider must implement.

Using an abstract base class means the rest of the application
(main.py) only ever talks to `AIProvider`, never to a specific SDK.
Adding support for a new, genuinely different provider means writing
one class here that implements `generate_structured` — nothing else in
the project needs to change.
"""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class AIProvider(ABC):
    """Abstract interface for any AI provider used in this project."""

    @abstractmethod
    def generate_structured(self, listing: dict, schema: type[T]) -> T:
        """Send a listing to the model and return a validated result.

        Args:
            listing: Cleaned laptop listing data.
            schema: Pydantic model describing the expected output shape.

        Returns:
            A validated instance of `schema`.
        """
        raise NotImplementedError