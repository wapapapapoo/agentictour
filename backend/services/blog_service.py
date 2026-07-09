from sqlalchemy.orm import Session

from models.blog import BlogGeneration, BlogMaterial
from schemas.blog import BlogContentType, BlogGenerateRequest, BlogMaterialCreate, BlogWritingStyle

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


def generate_mock_content(material: BlogMaterial, req: BlogGenerateRequest) -> dict[str, str]:
    style_map = {
        "guide": "攻略型",
        "story": "故事型",
        "casual": "轻松分享型",
        "promotion": "种草型",
    }

    type_map = {
        "blog": "游记初稿",
        "social_post": "社交平台文案",
        "title_tags": "标题和标签",
    }

    content_type_cn = type_map.get(req.content_type, req.content_type)
    style_cn = style_map.get(req.writing_style, req.writing_style)
    title = f"{material.destination}旅行记录：{material.title}"

    if req.content_type == "title_tags":
        content = (
            f"标题建议：\n"
            f"1. {material.destination}旅行记录：一次轻松又真实的出行\n"
            f"2. {material.destination}游玩整理：路线、美食与感受\n"
            f"3. 我的{material.destination}之旅：慢节奏体验分享\n"
        )
    elif req.content_type == "social_post":
        content = (
            f"这次去了{material.destination}，整体感受是："
            f"{material.feeling_text or '行程比较顺利，体验不错。'}\n\n"
            f"行程安排：{material.itinerary_text}\n\n"
            f"美食体验：{material.food_text or '暂无详细美食记录。'}\n\n"
            f"适合想要轻松出行、不想安排太满的朋友。"
        )
    else:
        content = (
            f"# {title}\n\n"
            f"这是一篇根据用户旅行素材生成的{content_type_cn}，"
            f"当前写作风格为{style_cn}。\n\n"
            f"## 行程概况\n"
            f"{material.itinerary_text}\n\n"
            f"## 美食体验\n"
            f"{material.food_text or '用户暂未补充详细美食记录。'}\n\n"
            f"## 照片与场景\n"
            f"{material.photo_text or '用户暂未补充照片描述。'}\n\n"
            f"## 消费情况\n"
            f"{material.expense_text or '用户暂未补充消费摘要。'}\n\n"
            f"## 个人感受\n"
            f"{material.feeling_text or '用户暂未补充个人感受。'}\n"
        )

    return {
        "title": title,
        "content": content,
        "tags": f"{material.destination},旅行,游记,{style_cn}",
        "risk_note": "当前内容为模拟生成结果，后续接入 Dify 后将替换为真实模型输出。",
    }


def create_generation(db: Session, req: BlogGenerateRequest) -> BlogGeneration:
    if req.content_type not in VALID_CONTENT_TYPES:
        raise ValueError("invalid content_type")

    if req.writing_style not in VALID_WRITING_STYLES:
        raise ValueError("invalid writing_style")

    material = get_material(db, req.material_id, req.user_id)
    if material is None:
        raise LookupError("material not found")

    mock_result = generate_mock_content(material, req)

    generation = BlogGeneration(
        material_id=req.material_id,
        user_id=req.user_id,
        content_type=req.content_type,
        writing_style=req.writing_style,
        generated_title=mock_result["title"],
        generated_content=mock_result["content"],
        tags=mock_result["tags"],
        risk_note=mock_result["risk_note"],
    )

    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def list_generations(db: Session, user_id: str) -> list[dict]:
    query = (
        db.query(BlogGeneration, BlogMaterial)
        .join(BlogMaterial, BlogGeneration.material_id == BlogMaterial.id)
        .filter(BlogGeneration.user_id == user_id)
        .order_by(BlogGeneration.created_at.desc())
    )

    rows = query.all()

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
