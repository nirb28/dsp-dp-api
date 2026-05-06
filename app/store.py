import json
from datetime import UTC, datetime
from pathlib import Path

from app.models import DataProductRecord, ParsedDataProduct


class DataProductStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.products_dir = state_dir / "products"
        self.products_dir.mkdir(parents=True, exist_ok=True)

    def upsert(self, parsed: ParsedDataProduct) -> DataProductRecord:
        project_id = parsed.document.project.id
        existing = self.get(project_id)
        created_at = existing.created_at if existing else datetime.now(UTC)
        record = DataProductRecord(
            version=parsed.document.version,
            project=parsed.document.project,
            connection=parsed.document.connection,
            mdl=parsed.mdl_json,
            sql_pairs=parsed.sql_pairs_json,
            created_at=created_at,
            updated_at=datetime.now(UTC),
        )
        self._record_path(project_id).write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get(self, project_id: str) -> DataProductRecord | None:
        path = self._record_path(project_id)
        if not path.exists():
            return None
        return DataProductRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: DataProductRecord) -> DataProductRecord:
        record.updated_at = datetime.now(UTC)
        self._record_path(record.project.id).write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def list(self) -> list[DataProductRecord]:
        records = []
        for path in sorted(self.products_dir.glob("*.json")):
            records.append(DataProductRecord.model_validate_json(path.read_text(encoding="utf-8")))
        return records

    def _record_path(self, project_id: str) -> Path:
        safe_project_id = project_id.replace("/", "_").replace("\\", "_")
        return self.products_dir / f"{safe_project_id}.json"


class ManifestRegistry:
    def __init__(self, registry_dir: Path) -> None:
        self.registry_dir = registry_dir
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def write_manifest(self, record: DataProductRecord) -> Path:
        payload = {
            "source": record.connection.type,
            "manifest": record.mdl,
            "connectionInfo": record.connection.properties,
        }
        path = self._manifest_path(record.project.id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def _manifest_path(self, project_id: str) -> Path:
        safe_project_id = project_id.replace("/", "_").replace("\\", "_")
        return self.registry_dir / f"{safe_project_id}.json"
