"""MCP tool input/output schemas.

Defines explicit input and output contracts for all MCP tools.
"""

from pydantic import BaseModel, Field, field_validator


class ResolveSymbolInput(BaseModel):
    """Input for resolve_symbol tool."""

    repo_id: str = Field(..., min_length=1, pattern=r"^repo:.+")
    qualified_name: str = Field(..., min_length=1)
    kind: str | None = None
    file_id: str | None = None

    @field_validator("qualified_name")
    @classmethod
    def validate_qualified_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("qualified_name must not be empty or whitespace")
        return v


class GetSymbolContextInput(BaseModel):
    """Input for get_symbol_context tool."""

    symbol_id: str = Field(..., min_length=1)

    @field_validator("symbol_id")
    @classmethod
    def validate_symbol_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("symbol_id must not be empty or whitespace")
        return v


class RefreshSymbolReferencesInput(BaseModel):
    """Input for refresh_symbol_references tool."""

    symbol_id: str = Field(..., min_length=1)

    @field_validator("symbol_id")
    @classmethod
    def validate_symbol_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("symbol_id must not be empty or whitespace")
        return v


class GetSymbolReferencesInput(BaseModel):
    """Input for get_symbol_references tool."""

    symbol_id: str = Field(..., min_length=1)

    @field_validator("symbol_id")
    @classmethod
    def validate_symbol_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("symbol_id must not be empty or whitespace")
        return v


class AnalyzeSymbolRiskInput(BaseModel):
    """Input for analyze_symbol_risk tool."""

    symbol_id: str = Field(..., min_length=1)

    @field_validator("symbol_id")
    @classmethod
    def validate_symbol_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("symbol_id must not be empty or whitespace")
        return v


class AnalyzeTargetSetRiskInput(BaseModel):
    """Input for analyze_target_set_risk tool."""

    symbol_ids: list[str] = Field(..., min_length=1)

    @field_validator("symbol_ids")
    @classmethod
    def validate_symbol_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("symbol_ids must not be empty")
        for i, sid in enumerate(v):
            if not sid.strip():
                raise ValueError(f"symbol_ids[{i}] must not be empty or whitespace")
        return v
