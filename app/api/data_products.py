from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from httpx import HTTPError

from app.errors import DataProductError
from app.models import AskRequest, DataProductRecord, DeployResponse
from app.parser import parse_data_product_yaml
from app.store import DataProductStore, ManifestRegistry
from app.wren_client import WrenAIClient
from app.dependencies import get_manifest_registry, get_store, get_wren_client

router = APIRouter(prefix="/api/v1/data-products", tags=["data-products"])


@router.post("", response_model=DeployResponse)
async def create_data_product(
    file: UploadFile = File(...),
    store: DataProductStore = Depends(get_store),
) -> DeployResponse:
    try:
        content = (await file.read()).decode("utf-8")
        parsed = parse_data_product_yaml(content)
        record = store.upsert(parsed)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 encoded") from exc
    except DataProductError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return DeployResponse(project_id=record.project.id, status=record.status)


@router.post("/{project_id}/deploy", response_model=DeployResponse)
async def deploy_data_product(
    project_id: str,
    store: DataProductStore = Depends(get_store),
    manifest_registry: ManifestRegistry = Depends(get_manifest_registry),
    wren_client: WrenAIClient = Depends(get_wren_client),
) -> DeployResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Data product was not found")
    try:
        manifest_registry.write_manifest(record)
        response = await wren_client.deploy_semantics(record)
    except HTTPError as exc:
        record.status = "failed"
        record.error = f"WrenAI service request failed: {exc}"
        store.save(record)
        raise HTTPException(status_code=502, detail=record.error) from exc

    record.status = "deployed"
    record.mdl_hash = response.get("id") or response.get("mdl_hash") or wren_client.mdl_hash(record)
    record.error = None
    store.save(record)
    return DeployResponse(project_id=record.project.id, status=record.status)


@router.get("", response_model=list[DataProductRecord])
def list_data_products(store: DataProductStore = Depends(get_store)) -> list[DataProductRecord]:
    return store.list()


@router.get("/{project_id}", response_model=DataProductRecord)
def get_data_product(project_id: str, store: DataProductStore = Depends(get_store)) -> DataProductRecord:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Data product was not found")
    return record


@router.post("/{project_id}/ask")
async def ask_data_product(
    project_id: str,
    request: AskRequest,
    store: DataProductStore = Depends(get_store),
    wren_client: WrenAIClient = Depends(get_wren_client),
):
    record = _require_deployed_data_product(project_id, store)
    try:
        return await wren_client.ask(record, request)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"WrenAI service request failed: {exc}") from exc


@router.get("/{project_id}/ask/{query_id}/result")
async def get_ask_result(
    project_id: str,
    query_id: str,
    store: DataProductStore = Depends(get_store),
    wren_client: WrenAIClient = Depends(get_wren_client),
):
    _require_deployed_data_product(project_id, store)
    try:
        return await wren_client.ask_result(query_id)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"WrenAI service request failed: {exc}") from exc


@router.get("/{project_id}/ask/{query_id}/streaming-result")
async def get_ask_streaming_result(
    project_id: str,
    query_id: str,
    store: DataProductStore = Depends(get_store),
    wren_client: WrenAIClient = Depends(get_wren_client),
):
    _require_deployed_data_product(project_id, store)
    return StreamingResponse(wren_client.ask_streaming_result(query_id), media_type="text/event-stream")


def _require_deployed_data_product(project_id: str, store: DataProductStore) -> DataProductRecord:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Data product was not found")
    if record.status != "deployed":
        raise HTTPException(status_code=409, detail="Data product must be deployed before asking questions")
    return record
