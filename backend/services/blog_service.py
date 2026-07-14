import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from sqlalchemy.orm import Session

from models.blog import BlogGeneration, BlogMaterial, BlogPhoto
from schemas.blog import (
    BlogContentType,
    BlogGenerateRequest,
    BlogMaterialCreate,
    BlogWritingStyle,
)
from utils.dify_client import (
    DifyClient,
    DifyConfigError,
    DifyRequestError,
    DifyResponseError,
    DifyTimeoutError,
)

VALID_CONTENT_TYPES = {item.value for item in BlogContentType}
VALID_WRITING_STYLES = {item.value for item in BlogWritingStyle}
MAX_PHOTO_SIZE = 10 * 1024 * 1024
MAX_PHOTOS_PER_MATERIAL = 3
DEFAULT_PHOTO_DIR = Path(__file__).resolve().parents[1] / "uploads" / "blog"


def create_material(db: Session, data: BlogMaterialCreate) -> BlogMaterial:
    material = BlogMaterial(**data.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def get_material(
    db: Session,
    material_id: int,
    user_id: int | None = None,
) -> BlogMaterial | None:
    query = db.query(BlogMaterial).filter(BlogMaterial.id == material_id)
    if user_id is not None:
        query = query.filter(BlogMaterial.user_id == user_id)
    return query.first()


def create_photo(
    db: Session,
    *,
    material_id: int,
    user_id: int,
    original_filename: str,
    content: bytes,
) -> BlogPhoto:
    if get_material(db, material_id, user_id) is None:
        raise LookupError("material not found")
    photo_count = (
        db.query(BlogPhoto)
        .filter(BlogPhoto.material_id == material_id, BlogPhoto.user_id == user_id)
        .count()
    )
    if photo_count >= MAX_PHOTOS_PER_MATERIAL:
        raise ValueError("each material can contain at most 3 photos")
    if not content:
        raise ValueError("image file is empty")
    if len(content) > MAX_PHOTO_SIZE:
        raise ValueError("image file must not exceed 10 MB")

    image_type = _detect_image_type(content)
    if image_type is None:
        raise ValueError("only JPG, PNG and WEBP images are supported")

    extension, content_type = image_type
    upload_dir = Path(os.getenv("BLOG_UPLOAD_DIR", str(DEFAULT_PHOTO_DIR)))
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{extension}"
    file_path = upload_dir / stored_filename
    file_path.write_bytes(content)

    photo = BlogPhoto(
        material_id=material_id,
        user_id=user_id,
        original_filename=Path(original_filename or "image").name[:255],
        stored_filename=stored_filename,
        content_type=content_type,
        file_size=len(content),
    )
    try:
        db.add(photo)
        db.commit()
        db.refresh(photo)
    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise
    return photo


def _detect_image_type(content: bytes) -> tuple[str, str] | None:
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        return ".jpg", "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if (
        len(content) >= 12
        and content.startswith(b"RIFF")
        and content[8:12] == b"WEBP"
    ):
        return ".webp", "image/webp"
    return None


def get_photo(db: Session, photo_id: int, user_id: int) -> BlogPhoto | None:
    return (
        db.query(BlogPhoto)
        .filter(BlogPhoto.id == photo_id, BlogPhoto.user_id == user_id)
        .first()
    )


def get_photo_path(photo: BlogPhoto) -> Path:
    upload_dir = Path(os.getenv("BLOG_UPLOAD_DIR", str(DEFAULT_PHOTO_DIR))).resolve()
    file_path = (upload_dir / photo.stored_filename).resolve()
    if file_path.parent != upload_dir or not file_path.is_file():
        raise FileNotFoundError("photo file not found")
    return file_path


def _to_dify_inputs(
    material: BlogMaterial,
    req: BlogGenerateRequest,
    photos: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    def text(value: Any) -> str:
        return "" if value is None else str(value)

    return {
        "material_id": text(material.id),
        "user_id": str(req.user_id),
        "title": material.title,
        "destination": material.destination,
        "start_date": text(material.start_date),
        "end_date": text(material.end_date),
        "people_count": text(material.people_count),
        "itinerary_text": material.itinerary_text,
        "food_text": text(material.food_text),
        "photo_text": text(material.photo_text),
        "expense_text": text(material.expense_text),
        "feeling_text": text(material.feeling_text),
        "content_type": req.content_type.value,
        "writing_style": req.writing_style.value,
        "photos": photos or [],
    }


def _upload_photo_to_dify(
    client: DifyClient,
    photo: BlogPhoto,
    user: str,
) -> dict[str, str]:
    upload_url = os.getenv("DIFY_BLOG_FILE_UPLOAD_URL")
    if not upload_url:
        if "/workflows/run" not in client.url:
            raise DifyConfigError("Dify workflow URL must end with /workflows/run.")
        upload_url = client.url.replace("/workflows/run", "/files/upload", 1)

    try:
        file_path = get_photo_path(photo)
    except FileNotFoundError as exc:
        raise DifyResponseError(f"Photo file {photo.id} was not found.") from exc

    try:
        with file_path.open("rb") as image_file:
            response = client.session.post(
                upload_url,
                headers={"Authorization": f"Bearer {client.api_key}"},
                files={
                    "file": (
                        photo.original_filename,
                        image_file,
                        photo.content_type,
                    )
                },
                data={"user": user},
                timeout=client.timeout,
            )
    except requests.exceptions.Timeout as exc:
        raise DifyTimeoutError("Dify file upload timed out.") from exc
    except requests.exceptions.RequestException as exc:
        raise DifyRequestError(f"Dify file upload failed: {exc}") from exc

    if response.status_code >= 400:
        client._raise_http_error(response)

    body = client._parse_json(response)
    upload_file_id = body.get("id") if isinstance(body, dict) else None
    if not isinstance(upload_file_id, str) or not upload_file_id:
        raise DifyResponseError("Dify file upload response is missing id.")

    return {
        "type": "image",
        "transfer_method": "local_file",
        "upload_file_id": upload_file_id,
    }


def _extract_generation_result(workflow_response: dict[str, Any]) -> dict[str, str]:
    data = workflow_response.get("data")
    outputs = data.get("outputs") if isinstance(data, dict) else None
    if not isinstance(outputs, dict):
        raise DifyResponseError("Dify workflow outputs must be an object.")

    result = outputs.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError as exc:
            raise DifyResponseError(
                "Dify workflow output 'result' must be valid JSON."
            ) from exc

    if not isinstance(result, dict):
        raise DifyResponseError("Dify workflow output 'result' must be an object.")

    generated_content = result.get("generated_content")
    if not isinstance(generated_content, str) or not generated_content.strip():
        raise DifyResponseError("Dify result is missing generated_content.")

    parsed = {"generated_content": generated_content.strip()}
    for field in ("generated_title", "tags", "risk_note"):
        value = result.get(field)
        parsed[field] = value.strip() if isinstance(value, str) else ""
    return parsed


def _generate_blog_content(
    material: BlogMaterial,
    req: BlogGenerateRequest,
) -> dict[str, str]:
    client = DifyClient(
        api_key=os.getenv("DIFY_BLOG_API_KEY") or os.getenv("DIFY_API_KEY"),
        url=os.getenv("DIFY_BLOG_URL") or os.getenv("DIFY_URL"),
        timeout=float(os.getenv("DIFY_TIMEOUT", "120")),
    )
    user = str(req.user_id)
    photos = sorted(material.photos, key=lambda photo: photo.id)[
        :MAX_PHOTOS_PER_MATERIAL
    ]
    dify_photos = [_upload_photo_to_dify(client, photo, user) for photo in photos]
    response = client.run_workflow(
        user=user,
        inputs=_to_dify_inputs(material, req, dify_photos),
    )
    return _extract_generation_result(response)


def create_generation(db: Session, req: BlogGenerateRequest) -> BlogGeneration:
    if req.content_type not in VALID_CONTENT_TYPES:
        raise ValueError("invalid content_type")

    if req.writing_style not in VALID_WRITING_STYLES:
        raise ValueError("invalid writing_style")

    material = get_material(db, req.material_id, req.user_id)
    if material is None:
        raise LookupError("material not found")

    result = _generate_blog_content(material, req)
    generation = BlogGeneration(
        material_id=req.material_id,
        user_id=req.user_id,
        content_type=req.content_type,
        writing_style=req.writing_style,
        generated_title=result["generated_title"] or None,
        generated_content=result["generated_content"],
        tags=result["tags"] or None,
        risk_note=result["risk_note"] or None,
    )

    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def list_generations(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(BlogGeneration, BlogMaterial)
        .join(BlogMaterial, BlogGeneration.material_id == BlogMaterial.id)
        .filter(BlogGeneration.user_id == user_id)
        .order_by(BlogGeneration.created_at.desc())
        .all()
    )

    return [
        {
            "id": generation.id,
            "material_id": generation.material_id,
            "material_title": material.title,
            "destination": material.destination,
            "content_type": generation.content_type,
            "writing_style": generation.writing_style,
            "generated_title": generation.generated_title,
            "created_at": generation.created_at,
        }
        for generation, material in rows
    ]


def get_generation(
    db: Session,
    generation_id: int,
    user_id: int | None = None,
) -> BlogGeneration | None:
    query = db.query(BlogGeneration).filter(BlogGeneration.id == generation_id)
    if user_id is not None:
        query = query.filter(BlogGeneration.user_id == user_id)
    return query.first()


def delete_generation(db: Session, generation_id: int, user_id: int) -> bool:
    generation = get_generation(db, generation_id, user_id)
    if generation is None:
        return False

    db.delete(generation)
    db.commit()
    return True
