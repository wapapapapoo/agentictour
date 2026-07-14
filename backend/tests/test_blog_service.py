import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("pymysql")

from database import Base
from models.blog import BlogGeneration, BlogMaterial, BlogPhoto
from schemas.blog import BlogGenerateRequest, BlogMaterialCreate
from services import blog_service
from utils.dify_client import DifyResponseError

REAL_GENERATE_BLOG_CONTENT = blog_service._generate_blog_content


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
        tables=[BlogMaterial.__table__, BlogPhoto.__table__, BlogGeneration.__table__],
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(
            bind=engine,
            tables=[
                BlogGeneration.__table__,
                BlogPhoto.__table__,
                BlogMaterial.__table__,
            ],
        )


def _material_data(user_id: int = 1) -> BlogMaterialCreate:
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


def _generate_request(material_id: int, user_id: int = 1) -> BlogGenerateRequest:
    return BlogGenerateRequest(
        material_id=material_id,
        user_id=user_id,
        content_type="blog",
        writing_style="guide",
    )


def test_blog_material_rejects_blank_required_text() -> None:
    with pytest.raises(ValidationError):
        BlogMaterialCreate(
            user_id=1,
            title=" ",
            destination="上海",
            itinerary_text="外滩、武康路和豫园。",
        )


def test_blog_material_rejects_invalid_date_range() -> None:
    with pytest.raises(ValidationError):
        BlogMaterialCreate(
            user_id=1,
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
            user_id=1,
            content_type="bad_type",
            writing_style="guide",
        )


def test_create_generation_requires_material_owner(db_session: Session) -> None:
    material = blog_service.create_material(db_session, _material_data(user_id=1))

    with pytest.raises(LookupError):
        blog_service.create_generation(
            db_session,
            _generate_request(material_id=material.id, user_id=2),
        )


def test_generation_queries_are_limited_to_user(db_session: Session) -> None:
    user_a_material = blog_service.create_material(db_session, _material_data(1))
    user_b_material = blog_service.create_material(db_session, _material_data(2))

    user_a_generation = blog_service.create_generation(
        db_session,
        _generate_request(user_a_material.id, 1),
    )
    user_b_generation = blog_service.create_generation(
        db_session,
        _generate_request(user_b_material.id, 2),
    )

    user_a_rows = blog_service.list_generations(db_session, 1)

    assert [row["id"] for row in user_a_rows] == [user_a_generation.id]
    assert blog_service.get_generation(db_session, user_b_generation.id, 1) is None
    assert blog_service.delete_generation(db_session, user_b_generation.id, 1) is False
    assert blog_service.delete_generation(db_session, user_b_generation.id, 2) is True


def test_to_dify_inputs_matches_workflow_variables(db_session: Session) -> None:
    material = blog_service.create_material(db_session, _material_data())

    inputs = blog_service._to_dify_inputs(material, _generate_request(material.id))

    assert inputs["material_id"] == str(material.id)
    assert inputs["user_id"] == "1"
    assert inputs["start_date"] == "2026-07-20"
    assert inputs["content_type"] == "blog"
    assert inputs["writing_style"] == "guide"
    assert inputs["photo_text"] == ""
    assert inputs["photos"] == []


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


def test_create_photo_saves_file_for_material_owner(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BLOG_UPLOAD_DIR", str(tmp_path))
    material = blog_service.create_material(db_session, _material_data())
    png_content = b"\x89PNG\r\n\x1a\nimage-data"

    photo = blog_service.create_photo(
        db_session,
        material_id=material.id,
        user_id=material.user_id,
        original_filename="trip.png",
        content=png_content,
    )

    assert photo.content_type == "image/png"
    assert photo.file_size == len(png_content)
    assert blog_service.get_photo_path(photo).read_bytes() == png_content


def test_create_photo_rejects_unsupported_file(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BLOG_UPLOAD_DIR", str(tmp_path))
    material = blog_service.create_material(db_session, _material_data())

    with pytest.raises(ValueError, match="only JPG, PNG and WEBP"):
        blog_service.create_photo(
            db_session,
            material_id=material.id,
            user_id=material.user_id,
            original_filename="notes.txt",
            content=b"not an image",
        )


def test_create_photo_limits_material_to_three_photos(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BLOG_UPLOAD_DIR", str(tmp_path))
    material = blog_service.create_material(db_session, _material_data())
    png_content = b"\x89PNG\r\n\x1a\nimage-data"

    for index in range(3):
        blog_service.create_photo(
            db_session,
            material_id=material.id,
            user_id=material.user_id,
            original_filename=f"trip-{index}.png",
            content=png_content,
        )

    with pytest.raises(ValueError, match="at most 3 photos"):
        blog_service.create_photo(
            db_session,
            material_id=material.id,
            user_id=material.user_id,
            original_filename="trip-4.png",
            content=png_content,
        )


def test_generate_blog_passes_uploaded_photos_to_workflow(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    material = blog_service.create_material(db_session, _material_data())
    photo = BlogPhoto(
        material_id=material.id,
        user_id=material.user_id,
        original_filename="trip.png",
        stored_filename="stored.png",
        content_type="image/png",
        file_size=10,
    )
    db_session.add(photo)
    db_session.commit()
    db_session.refresh(material)

    class FakeClient:
        def __init__(self) -> None:
            self.inputs = None

        def run_workflow(self, *, user, inputs):
            self.inputs = inputs
            return {
                "data": {
                    "outputs": {
                        "result": '{"generated_title":"title",'
                        '"generated_content":"content","tags":"tag",'
                        '"risk_note":"note"}'
                    }
                }
            }

    client = FakeClient()
    monkeypatch.setattr(blog_service, "DifyClient", lambda **kwargs: client)
    monkeypatch.setattr(
        blog_service,
        "_upload_photo_to_dify",
        lambda client, photo, user: {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": "dify-file-1",
        },
    )

    result = REAL_GENERATE_BLOG_CONTENT(
        material,
        _generate_request(material.id),
    )

    assert result["generated_content"] == "content"
    assert client.inputs["photos"] == [
        {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": "dify-file-1",
        }
    ]
