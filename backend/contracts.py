import math
from pydantic import Field
from pydantic import BaseModel, ConfigDict, field_validator

class PatientInput(BaseModel):
    """Validated clinical input for the heart disease prediction model."""

    model_config = ConfigDict(extra="forbid")

    age: int
    sex: int
    cp: int
    trestbps: int
    chol: int
    fbs: int
    restecg: int
    thalach: int
    exang: int
    oldpeak: float
    slope: int
    ca: int
    thal: int

    @field_validator("*", mode="before")
    @classmethod
    def reject_booleans(cls, value):
        if isinstance(value, bool):
            raise ValueError("Use a numeric measurement or category code, not a boolean.")
        return value

    @field_validator("*")
    @classmethod
    def values_must_be_finite(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Each patient value must be finite.")
        return value

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int) -> int:
        if not 18 <= value <= 100:
            raise ValueError("Age must be between 18 and 100.")
        return value

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, value: int) -> int:
        if value not in [0, 1]:
            raise ValueError("Sex must be 0 or 1.")
        return value

    @field_validator("cp")
    @classmethod
    def validate_cp(cls, value: int) -> int:
        if value not in [1, 2, 3, 4]:
            raise ValueError("cp must be 1, 2, 3, or 4.")
        return value

    @field_validator("trestbps")
    @classmethod
    def validate_trestbps(cls, value: int) -> int:
        if not 70 <= value <= 250:
            raise ValueError("trestbps must be between 70 and 250.")
        return value

    @field_validator("chol")
    @classmethod
    def validate_chol(cls, value: int) -> int:
        if not 100 <= value <= 600:
            raise ValueError("chol must be between 100 and 600.")
        return value

    @field_validator("fbs")
    @classmethod
    def validate_fbs(cls, value: int) -> int:
        if value not in [0, 1]:
            raise ValueError("fbs must be 0 or 1.")
        return value

    @field_validator("restecg")
    @classmethod
    def validate_restecg(cls, value: int) -> int:
        if value not in [0, 1, 2]:
            raise ValueError("restecg must be 0, 1, or 2.")
        return value

    @field_validator("thalach")
    @classmethod
    def validate_thalach(cls, value: int) -> int:
        if not 40 <= value <= 250:
            raise ValueError("thalach must be between 40 and 250.")
        return value

    @field_validator("exang")
    @classmethod
    def validate_exang(cls, value: int) -> int:
        if value not in [0, 1]:
            raise ValueError("exang must be 0 or 1.")
        return value

    @field_validator("oldpeak")
    @classmethod
    def validate_oldpeak(cls, value: float) -> float:
        if not 0 <= value <= 10:
            raise ValueError("oldpeak must be between 0 and 10.")
        return value

    @field_validator("slope")
    @classmethod
    def validate_slope(cls, value: int) -> int:
        if value not in [1, 2, 3]:
            raise ValueError("slope must be 1, 2, or 3.")
        return value

    @field_validator("ca")
    @classmethod
    def validate_ca(cls, value: int) -> int:
        if value not in [0, 1, 2, 3]:
            raise ValueError("ca must be between 0 and 3.")
        return value

    @field_validator("thal")
    @classmethod
    def validate_thal(cls, value: int) -> int:
        if value not in [3, 6, 7]:
            raise ValueError("thal must be 3, 6, or 7.")
        return value


class SimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original: PatientInput
    modified: PatientInput


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    role: str | None = None

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value
