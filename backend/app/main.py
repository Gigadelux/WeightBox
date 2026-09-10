from fastapi import FastAPI


app = FastAPI(
    title="WeightBox API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "WeightBox API"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }