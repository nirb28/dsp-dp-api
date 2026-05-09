import base64
import json

from app.parser import parse_data_product_yaml
from app.store import DataProductStore, ManifestRegistry


VALID_YAML = """
version: "1.0"
project:
  id: "dp_01"
  name: "DP 01"
connection:
  type: "postgres"
  properties:
    database: "warehouse"
    port: 5432
mdl: |
  {"models": []}
semantics:
  sql_pairs: |
    []
"""


def test_store_persists_data_product(tmp_path):
    parsed = parse_data_product_yaml(VALID_YAML)
    store = DataProductStore(tmp_path)

    record = store.upsert(parsed)
    loaded = store.get("dp_01")

    assert record.project.id == "dp_01"
    assert loaded is not None
    assert loaded.connection.properties["database"] == "warehouse"


def test_manifest_registry_writes_project_manifest(tmp_path):
    parsed = parse_data_product_yaml(VALID_YAML)
    record = DataProductStore(tmp_path / "state").upsert(parsed)
    registry = ManifestRegistry(tmp_path / "manifests")

    path = registry.write_manifest(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = json.loads(base64.b64decode(payload["manifestStr"]).decode("utf-8"))

    assert path.exists()
    assert path.name == "dp_01.json"
    assert payload["source"] == "postgres"
    assert payload["connectionInfo"]["database"] == "warehouse"
    assert payload["connectionInfo"]["port"] == "5432"
    assert manifest["catalog"] == "wren"
    assert manifest["schema"] == "public"
    assert manifest["dataSource"] == "postgres"
    assert manifest["layoutVersion"] == 1
