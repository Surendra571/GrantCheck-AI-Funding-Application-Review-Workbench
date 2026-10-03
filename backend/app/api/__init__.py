from fastapi import APIRouter
from app.api.assessments import router as assessments_router
from app.api.documents import router as documents_router
from app.api.reviews import router as reviews_router
from app.api.supporting_docs import router as supporting_docs_router
from app.api.summaries import router as summaries_router

api_router = APIRouter(prefix="/api")

api_router.include_router(assessments_router)
api_router.include_router(documents_router)
api_router.include_router(reviews_router)
api_router.include_router(supporting_docs_router)
api_router.include_router(summaries_router)
