from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class FunctionBase(BaseModel):
    """Model for User Input To Run the SAP function."""

    # Optional: if the caller does not provide a process_id, the server will generate one.
    process_id: Optional[str] = Field(
        default=None,
        description="Optional unique process ID. If omitted, the server will create one."
    )

    function_to_run: str = Field(
        ..., description="Name of the function, which must be run internally"
    )

    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional dictionary of parameters to pass to the function"
    )


class FunctionResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None


class JobResult(BaseModel):
    process_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
