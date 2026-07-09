from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.blog import (
    BlogGenerateRequest,
    BlogGenerationListItem,
    BlogGenerationResponse,
    BlogMaterialCreate,
    BlogMaterialResponse,
)
from services import blog_service

router = APIRouter(prefix="/api/blog", tags=["旅游博客辅助创作"])


@router.post("/materials", response_model=BlogMaterialResponse)
def create_material(data: BlogMaterialCreate, db: Session = Depends(get_db)):
    return blog_service.create_material(db, data)


@router.get("/materials/{material_id}", response_model=BlogMaterialResponse)
def get_material(
    material_id: int = Path(..., gt=0),
    user_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    material = blog_service.get_material(db, material_id, user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="素材不存在")
    return material


@router.post("/generate", response_model=BlogGenerationResponse)
def generate_blog(data: BlogGenerateRequest, db: Session = Depends(get_db)):
    try:
        return blog_service.create_generation(db, data)
    except LookupError:
        raise HTTPException(status_code=404, detail="素材不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/generations", response_model=list[BlogGenerationListItem])
def list_generations(
    user_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    return blog_service.list_generations(db, user_id)


@router.get("/generations/{generation_id}", response_model=BlogGenerationResponse)
def get_generation(
    generation_id: int = Path(..., gt=0),
    user_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    generation = blog_service.get_generation(db, generation_id, user_id)
    if generation is None:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    return generation


@router.delete("/generations/{generation_id}")
def delete_generation(
    generation_id: int = Path(..., gt=0),
    user_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    ok = blog_service.delete_generation(db, generation_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="生成记录不存在")

    return {"message": "删除成功"}
