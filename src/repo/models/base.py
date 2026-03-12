"""Base model definitions."""

from dataclasses import dataclass, asdict


@dataclass
class BaseModel:
    """Base class for all models."""

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return asdict(self)
