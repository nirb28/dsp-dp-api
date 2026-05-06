from fastapi import FastAPI

from app.api.data_products import router as data_products_router

app = FastAPI(title="DSP Data Product API", version="0.1.0")
app.include_router(data_products_router)


@app.get("/health")
def health():
    return {"status": "ok"}
