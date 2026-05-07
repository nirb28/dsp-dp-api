import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.errors import DataProductError
from app.models import DataProductDocument, ParsedDataProduct, SqlPair


def parse_data_product_yaml(content: str) -> ParsedDataProduct:
    try:
        raw = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise DataProductError(f"Invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise DataProductError("Data Product YAML must contain an object at the document root")

    try:
        document = DataProductDocument.model_validate(raw)
    except ValidationError as exc:
        raise DataProductError(str(exc)) from exc

    mdl_json = _normalize_mdl(_parse_json_object(document.mdl, "mdl"))
    sql_pairs_json = _parse_sql_pairs(document.semantics.sql_pairs if document.semantics else None)

    return ParsedDataProduct(document=document, mdl_json=mdl_json, sql_pairs_json=sql_pairs_json)


def parse_data_product_file(path: Path) -> ParsedDataProduct:
    return parse_data_product_yaml(path.read_text(encoding="utf-8"))


def _parse_json_object(value: str, field_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DataProductError(f"{field_name} must be a valid raw JSON string: {exc}") from exc

    if not isinstance(parsed, dict):
        raise DataProductError(f"{field_name} must decode to a JSON object")

    return parsed


def _parse_sql_pairs(value: str | None) -> list[SqlPair]:
    if value is None or value.strip() == "":
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DataProductError(f"semantics.sql_pairs must be a valid raw JSON string: {exc}") from exc

    if not isinstance(parsed, list):
        raise DataProductError("semantics.sql_pairs must decode to a JSON array")

    try:
        return [SqlPair.model_validate(item) for item in parsed]
    except ValidationError as exc:
        raise DataProductError(str(exc)) from exc


def _normalize_mdl(mdl: dict[str, Any]) -> dict[str, Any]:
    mdl = dict(mdl)
    mdl["models"] = [_normalize_model(model) for model in mdl.get("models", [])]
    mdl["relationships"] = [_normalize_relationship(relationship) for relationship in mdl.get("relationships", [])]
    mdl["metrics"] = [_normalize_metric(metric) for metric in mdl.get("metrics", [])]
    mdl.setdefault("views", [])
    return mdl


def _normalize_model(model: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(model)
    table_reference = normalized.get("tableReference")
    if isinstance(table_reference, str):
        normalized["tableReference"] = {"table": table_reference}
    primary_key = next(
        (column["name"] for column in normalized.get("columns", []) if column.get("primaryKey") is True),
        None,
    )
    if primary_key and "primaryKey" not in normalized:
        normalized["primaryKey"] = primary_key
    return normalized


def _normalize_relationship(relationship: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(relationship)
    if "models" not in normalized and "from" in normalized and "to" in normalized:
        normalized["models"] = [normalized.pop("from"), normalized.pop("to")]
    join_type = normalized.get("joinType")
    if isinstance(join_type, str):
        normalized["joinType"] = join_type.upper()
    return normalized


def _normalize_metric(metric: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(metric)
    if "baseObject" not in normalized and "model" in normalized:
        normalized["baseObject"] = normalized.pop("model")
    measure = normalized.get("measure")
    if isinstance(measure, str):
        normalized["measure"] = [
            {
                "name": normalized["name"],
                "type": "DOUBLE",
                "expression": measure,
            }
        ]
    normalized.setdefault("dimension", [])
    normalized.setdefault("timeGrain", [])
    if "baseObject" not in normalized:
        raise DataProductError(f"Metric '{normalized.get('name', '<unknown>')}' must include baseObject or model")
    return normalized
