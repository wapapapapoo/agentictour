import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("pymysql")

from database import Base
from models.blog import BlogGeneration, BlogMaterial
from schemas.blog import BlogGenerateRequest, BlogMaterialCreate
from services import blog_service
from utils.dify_client import DifyResponseError


@pytest.fixture(autouse=True)
def mock_blog_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        blog_service,
        "_generate_blog_content",
        lambda material, req: {
            "generated_title": "test title",
            "generated_content": "test content",
            "tags": "travel,test",
            "risk_note": "test risk note",
        },
    )


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[BlogMaterial.__table__, BlogGeneration.__table__],
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(
            bind=engine,
            tables=[BlogGeneration.__table__, BlogMaterial.__table__],
        )


def _material_data(user_id: str = "user-001") -> BlogMaterialCreate:
    return BlogMaterialCreate(
        user_id=user_id,
        title="上海周末旅行",
        destination="上海",
        start_date="2026-07-20",
        end_date="2026-07-22",
        people_count=2,
        itinerary_text="外滩、武康路和豫园。",
        food_text="生煎、小笼包。",
    )


def _generate_request(material_id: int, user_id: str = "user-001") -> BlogGenerateRequest:
    return BlogGenerateRequest(
        material_id=material_id,
        user_id=user_id,
        content_type="blog",
        writing_style="guide",
    )


def test_blog_material_rejects_blank_required_text() -> None:
    with pytest.raises(ValidationError):
        BlogMaterialCreate(
            user_id="user-001",
            title=" ",
            destination="上海",
            itinerary_text="外滩、武康路和豫园。",
        )


def test_blog_material_rejects_invalid_date_range() -> None:
    with pytest.raises(ValidationError):
        BlogMaterialCreate(
            user_id="user-001",
            title="上海周末旅行",
            destination="上海",
            start_date="2026-07-22",
            end_date="2026-07-20",
            itinerary_text="外滩、武康路和豫园。",
        )


def test_generate_request_rejects_invalid_enum_value() -> None:
    with pytest.raises(ValidationError):
        BlogGenerateRequest(
            material_id=1,
            user_id="user-001",
            content_type="bad_type",
            writing_style="guide",
        )


def test_create_generation_requires_material_owner(db_session: Session) -> None:
    material = blog_service.create_material(db_session, _material_data(user_id="owner"))

    with pytest.raises(LookupError):
        blog_service.create_generation(
            db_session,
            _generate_request(material_id=material.id, user_id="other-user"),
        )


def test_generation_queries_are_limited_to_user(db_session: Session) -> None:
    user_a_material = blog_service.create_material(db_session, _material_data("user-a"))
    user_b_material = blog_service.create_material(db_session, _material_data("user-b"))

    user_a_generation = blog_service.create_generation(
        db_session,
        _generate_request(user_a_material.id, "user-a"),
    )
    user_b_generation = blog_service.create_generation(
        db_session,
        _generate_request(user_b_material.id, "user-b"),
    )

    user_a_rows = blog_service.list_generations(db_session, "user-a")

    assert [row["id"] for row in user_a_rows] == [user_a_generation.id]
    assert blog_service.get_generation(db_session, user_b_generation.id, "user-a") is None
    assert blog_service.delete_generation(db_session, user_b_generation.id, "user-a") is False
    assert blog_service.delete_generation(db_session, user_b_generation.id, "user-b") is True


def test_to_dify_inputs_matches_workflow_variables(db_session: Session) -> None:
    material = blog_service.create_material(db_session, _material_data())

    inputs = blog_service._to_dify_inputs(material, _generate_request(material.id))

    assert inputs["material_id"] == str(material.id)
    assert inputs["start_date"] == "2026-07-20"
    assert inputs["content_type"] == "blog"
    assert inputs["writing_style"] == "guide"
    assert inputs["photo_text"] == ""


def test_extract_generation_result_parses_dify_result_json() -> None:
    response = {
        "data": {
            "outputs": {
                "result": '{"generated_title":"title","generated_content":"content",'
                '"tags":"travel,test","risk_note":"note"}'
            }
        }
    }

    result = blog_service._extract_generation_result(response)

    assert result == {
        "generated_title": "title",
        "generated_content": "content",
        "tags": "travel,test",
        "risk_note": "note",
    }


def test_extract_generation_result_rejects_invalid_result() -> None:
    with pytest.raises(DifyResponseError):
        blog_service._extract_generation_result(
            {"data": {"outputs": {"result": "not json"}}}
        )
