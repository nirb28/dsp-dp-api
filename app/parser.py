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

    mdl_json = _parse_json_object(document.mdl, "mdl")
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
