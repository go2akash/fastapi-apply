from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def root():
    return {"status": "ok"}


@router.get("/health")
def health():
    return {"ping": "pong"}
