"""Career simulation contracts."""

from pydantic import BaseModel, Field


class SimulationScenario(BaseModel):
    key: str
    label: str
    description: str | None = None


class SimulationRequest(BaseModel):
    scenario: str
    target_role: str | None = None
    assumptions: dict = Field(default_factory=dict)


class SimulationOutcome(BaseModel):
    label: str
    probability: float = Field(ge=0, le=1)
    detail: str | None = None


class SimulationResult(BaseModel):
    scenario: str
    outcomes: list[SimulationOutcome] = Field(default_factory=list)
    narrative: str | None = None
