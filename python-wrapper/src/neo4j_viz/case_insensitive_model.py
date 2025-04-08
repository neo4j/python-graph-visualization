from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator
from pydantic.alias_generators import to_snake


class CaseInsensitiveModel(BaseModel):
    @model_validator(mode="before")
    def _snake_property_keys(cls, values: Any) -> Any:
        def _snake(value: Any) -> Any:
            if isinstance(value, dict):
                return {to_snake(k): _snake(v) for k, v in value.items()}
            return value

        return _snake(values)
