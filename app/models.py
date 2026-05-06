from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectInfo(BaseModel):
    id: str
    name: str
    description: str | None = None


class ConnectionInfo(BaseModel):
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class SemanticsInfo(BaseModel):
    sql_pairs: str | None = None


class DataProductDocument(BaseModel):
    version: str
    project: ProjectInfo
    connection: ConnectionInfo
    mdl: str
    semantics: SemanticsInfo | None = None


class SqlPair(BaseModel):
    question: str
    sql: str


class ParsedDataProduct(BaseModel):
    document: DataProductDocument
    mdl_json: dict[str, Any]
    sql_pairs_json: list[SqlPair]


class DataProductRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    version: str
    project: ProjectInfo
    connection: ConnectionInfo
    mdl: dict[str, Any]
    sql_pairs: list[SqlPair] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["created", "deployed", "failed"] = "created"
    error: str | None = None


class DeployResponse(BaseModel):
    project_id: str
    status: str


class AskRequest(BaseModel):
    question: str
    thread_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
