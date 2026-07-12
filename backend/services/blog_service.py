import json
import os
from typing import Any

from sqlalchemy.orm import Session

from models.blog import BlogGeneration, BlogMaterial
from schemas.blog import (
    BlogContentType,
    BlogGenerateRequest,
    BlogMaterialCreate,
    BlogWritingStyle,
)
from utils.dify_client import DifyClient, DifyResponseError

VALID_CONTENT_TYPES = {item.value for item in BlogContentType}
VALID_WRITING_STYLES = {item.value for item in BlogWritingStyle}


def create_material(db: Session, data: BlogMaterialCreate) -> BlogMaterial:
    material = BlogMaterial(**data.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def get_material(
    db: Session,
    material_id: int,
    user_id: str | None = None,
) -> BlogMaterial | None:
    query = db.query(BlogMaterial).filter(BlogMaterial.id == material_id)
    if user_id is not None:
        query = query.filter(BlogMaterial.user_id == user_id)
    return query.first()


def _to_dify_inputs(
    material: BlogMaterial,
    req: BlogGenerateRequest,
) -> dict[str, str]:
    def text(value: Any) -> str:
        return "" if value is None else str(value)

    return {
        "material_id": text(material.id),
        "user_id": req.user_id,
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
    response = client.run_workflow(
        user=req.user_id,
        inputs=_to_dify_inputs(material, req),
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


def list_generations(db: Session, user_id: str) -> list[dict]:
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
    user_id: str | None = None,
) -> BlogGeneration | None:
    query = db.query(BlogGeneration).filter(BlogGeneration.id == generation_id)
    if user_id is not None:
        query = query.filter(BlogGeneration.user_id == user_id)
    return query.first()


def delete_generation(db: Session, generation_id: int, user_id: str) -> bool:
    generation = get_generation(db, generation_id, user_id)
    if generation is None:
        return False

    db.delete(generation)
    db.commit()
    return True
