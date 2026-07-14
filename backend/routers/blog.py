from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas.blog import (
    BlogGenerateRequest,
    BlogGenerationListItem,
    BlogGenerationResponse,
    BlogMaterialCreate,
    BlogMaterialResponse,
    BlogPhotoResponse,
)
from services import blog_service
from utils.dify_client import DifyConfigError, DifyError, DifyTimeoutError

router = APIRouter(prefix="/api/blog", tags=["旅游博客辅助创作"])


@router.post("/materials", response_model=BlogMaterialResponse)
def create_material(data: BlogMaterialCreate, db: Session = Depends(get_db)):
    return blog_service.create_material(db, data)


@router.get("/materials/{material_id}", response_model=BlogMaterialResponse)
def get_material(
    material_id: int = Path(..., gt=0),
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    material = blog_service.get_material(db, material_id, user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="素材不存在")
    return material


@router.post("/materials/{material_id}/photos", response_model=BlogPhotoResponse)
async def upload_photo(
    material_id: int = Path(..., gt=0),
    user_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        content = await file.read(blog_service.MAX_PHOTO_SIZE + 1)
        photo = blog_service.create_photo(
            db,
            material_id=material_id,
            user_id=user_id,
            original_filename=file.filename or "image",
            content=content,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="material not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await file.close()

    return {
        "id": photo.id,
        "material_id": photo.material_id,
        "user_id": photo.user_id,
        "original_filename": photo.original_filename,
        "content_type": photo.content_type,
        "file_size": photo.file_size,
        "file_url": f"/api/blog/photos/{photo.id}/file?user_id={photo.user_id}",
        "created_at": photo.created_at,
    }


@router.get("/photos/{photo_id}/file")
def get_photo_file(
    photo_id: int = Path(..., gt=0),
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    photo = blog_service.get_photo(db, photo_id, user_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="photo not found")
    try:
        file_path = blog_service.get_photo_path(photo)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="photo file not found")
    return FileResponse(
        path=file_path,
        media_type=photo.content_type,
        filename=photo.original_filename,
        content_disposition_type="inline",
    )


@router.post("/generate", response_model=BlogGenerationResponse)
def generate_blog(data: BlogGenerateRequest, db: Session = Depends(get_db)):
    try:
        return blog_service.create_generation(db, data)
    except LookupError:
        raise HTTPException(status_code=404, detail="素材不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DifyConfigError:
        raise HTTPException(status_code=503, detail="Dify service is not configured")
    except DifyTimeoutError:
        raise HTTPException(status_code=504, detail="Dify generation timed out")
    except DifyError:
        raise HTTPException(status_code=502, detail="Dify generation failed")


@router.get("/generations", response_model=list[BlogGenerationListItem])
def list_generations(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    return blog_service.list_generations(db, user_id)


@router.get("/generations/{generation_id}", response_model=BlogGenerationResponse)
def get_generation(
    generation_id: int = Path(..., gt=0),
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    generation = blog_service.get_generation(db, generation_id, user_id)
    if generation is None:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    return generation


@router.delete("/generations/{generation_id}")
def delete_generation(
    generation_id: int = Path(..., gt=0),
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    ok = blog_service.delete_generation(db, generation_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="生成记录不存在")

    return {"message": "删除成功"}
