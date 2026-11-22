from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import post_message

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description="Validates a short promotional message and publishes it to "
    "multiple third-party platforms independently.",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    details = [
        {k: v for k, v in error.items() if k != "ctx"} for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "success": False,
                "error": "validation_failed",
                "details": details,
            }
        ),
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/posting", response_model=PostingResponse)
async def posting(request: PostingRequest) -> PostingResponse:
    return await post_message(request.message)
