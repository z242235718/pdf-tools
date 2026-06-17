import json

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CreateTaskRequest(BaseModel):
    tool_type: str
    input_file_ids: list[int] = Field(default_factory=list)
    params: dict[str, object] = Field(default_factory=dict)


class TaskOutputFile(BaseModel):
    file_id: int
    download_url: str
    filename: str


class TaskResponse(BaseModel):
    task_id: int
    status: str
    tool_type: str
    progress: float
    error_code: str | None
    error_message: str | None
    warnings: list[str] = Field(default_factory=list)
    result_info: dict[str, object] = Field(default_factory=dict)

    @field_validator("result_info", mode="before")
    @classmethod
    def parse_result_info(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else {}
        if v is None:
            return {}
        return v
    output_files: list[TaskOutputFile] = Field(default_factory=list)
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
