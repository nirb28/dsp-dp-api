# dsp-dp-api

`dsp-dp-api` is a FastAPI control plane for WrenAI OS deployments that need multi-project and multi-model data product support.

## Responsibilities

- Parse Data Product YAML contracts.
- Validate `mdl` and `semantics.sql_pairs` as raw JSON strings embedded in YAML.
- Persist project-scoped state under `DSP_DP_API_STATE_DIR`.
- Create Data Products locally before deploying them to WrenAI.
- Write project manifests to `WREN_MANIFEST_REGISTRY_DIR` during deployment for WrenAI runtime routing.
- Proxy ask requests to WrenAI while enforcing the route `project_id`.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

## Run

```powershell
uvicorn app.main:app --reload --port 8080
```

## Create a Data Product

```powershell
curl.exe -X POST http://localhost:8080/api/v1/data-products `
  -F "file=@examples/data_product_example.yaml"
```

## Deploy a Data Product

```powershell
curl.exe -X POST http://localhost:8080/api/v1/data-products/dp_transaction_scoring_01/deploy
```

## Ask a Data Product

```powershell
curl.exe -X POST http://localhost:8080/api/v1/data-products/dp_transaction_scoring_01/ask `
  -H "Content-Type: application/json" `
  -d '{"question":"What is the average inference score?"}'
```

## API Endpoints

- `GET /health`
- `POST /api/v1/data-products`
- `GET /api/v1/data-products`
- `GET /api/v1/data-products/{project_id}`
- `POST /api/v1/data-products/{project_id}/deploy`
- `POST /api/v1/data-products/{project_id}/ask`

## Configuration

- `DSP_DP_API_STATE_DIR`: local API state directory.
- `WREN_AI_SERVICE_URL`: WrenAI service base URL.
- `WREN_IBIS_SERVER_URL`: Wren ibis server base URL reserved for future direct checks.
- `WREN_MANIFEST_REGISTRY_DIR`: directory shared with patched WrenAI containers for project manifests.

## Test

```powershell
pytest
```
