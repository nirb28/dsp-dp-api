from app.config import settings
from app.store import DataProductStore, ManifestRegistry
from app.wren_client import WrenAIClient


store = DataProductStore(settings.state_dir)
manifest_registry = ManifestRegistry(settings.wren_manifest_registry_dir)
wren_client = WrenAIClient(settings.wren_ai_service_url)


def get_store() -> DataProductStore:
    return store


def get_manifest_registry() -> ManifestRegistry:
    return manifest_registry


def get_wren_client() -> WrenAIClient:
    return wren_client
