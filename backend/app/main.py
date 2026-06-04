from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import AnalyzerError, analyze_palm_image

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(
    title="PalmLens API",
    version="0.1.0",
    description="Non-diagnostic palm image visual feature analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "PalmLens API",
        "scope": "visual-analysis-only",
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail="请上传 JPG、PNG 或 WebP 格式的手掌照片。",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空。")

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片不能超过 8MB。")

    try:
        return analyze_palm_image(data)
    except AnalyzerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

