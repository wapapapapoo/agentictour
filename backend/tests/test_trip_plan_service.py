from unittest.mock import MagicMock

from models.trip_plan import TripPlanRequest, TripPlanVersion
from schemas.trip_plan import TripPlanGenerateRequest, TripPlanReviseRequest
from services import trip_plan_service


def test_to_dify_inputs_keeps_all_values_as_strings() -> None:
    request = TripPlanGenerateRequest(
        trip_id=42,
        action="create",
        origin_city="出发城市",
        destination_city="目的地城市",
        start_date="2026-07-20",
        end_date="2026-07-23",
        people_count="2",
        budget_total="3000",
        interests="历史文化、美食、小众景点",
        hotel_level="经济型/舒适型/高端型",
        transport_preference="步行少/公共交通/打车优先/自驾",
        pace="轻松/普通/紧凑",
        special_requirements="老人同行、少走路、不去网红店",
        previous_plan_json="修改时传入上一版计划",
        revision_request="减少步行、加入夜生活、压缩预算等",
    )

    inputs = trip_plan_service._to_dify_inputs(request, "test-user-1")

    assert inputs == {
        "action": "create",
        "user_id": "test-user-1",
        "origin_city": "出发城市",
        "destination_city": "目的地城市",
        "start_date": "2026-07-20",
        "end_date": "2026-07-23",
        "people_count": "2",
        "budget_total": "3000",
        "interests": "历史文化、美食、小众景点",
        "hotel_level": "经济型/舒适型/高端型",
        "transport_preference": "步行少/公共交通/打车优先/自驾",
        "pace": "轻松/普通/紧凑",
        "special_requirements": "老人同行、少走路、不去网红店",
        "previous_plan_json": "修改时传入上一版计划",
        "revision_request": "减少步行、加入夜生活、压缩预算等",
    }
    assert all(isinstance(value, str) for value in inputs.values())
    assert "trip_id" not in inputs


def test_extract_plan_json_reads_dify_plan_json_string() -> None:
    workflow_response = {
        "workflow_run_id": "run-1",
        "data": {
            "outputs": {
                "plan_json": '{"title":"上海 3 日游","days":[],"budget":{}}',
            }
        },
    }

    plan_json = trip_plan_service._extract_plan_json(workflow_response)

    assert plan_json == {
        "title": "上海 3 日游",
        "days": [],
        "budget": {},
    }


def test_extract_plan_json_wraps_plain_text_answer() -> None:
    workflow_response = {
        "data": {
            "outputs": {
                "answer": "这里是一段普通文本计划。",
            }
        },
    }

    plan_json = trip_plan_service._extract_plan_json(workflow_response)

    assert plan_json["title"] == "行程计划"
    assert plan_json["summary"] == "这里是一段普通文本计划。"
    assert plan_json["days"] == []


def test_revise_plan_keeps_existing_trip_association(monkeypatch) -> None:
    request = TripPlanRequest(
        id=7,
        trip_id=42,
        user_id=1,
        action="create",
        origin_city="杭州",
        destination_city="上海",
        start_date="2026-07-20",
        end_date="2026-07-23",
        people_count="2",
        budget_total="3000",
        interests="历史文化",
        hotel_level="舒适型",
        transport_preference="公共交通",
        pace="轻松",
        special_requirements="",
    )
    latest = TripPlanVersion(id=8, request_id=7, version_no=1, plan_json="{}")
    workflow_inputs = []

    monkeypatch.setattr(trip_plan_service, "get_plan", lambda _db, _id: request)
    monkeypatch.setattr(
        trip_plan_service,
        "get_latest_version",
        lambda _db, _id: latest,
    )

    def fake_workflow(data, username):
        workflow_inputs.append(data)
        assert username == "test-user-1"
        return {"data": {"outputs": {"plan_json": "{}"}}}

    monkeypatch.setattr(trip_plan_service, "_run_trip_plan_workflow", fake_workflow)
    monkeypatch.setattr(
        trip_plan_service,
        "_get_username",
        lambda _db, _user_id: "test-user-1",
    )

    result = trip_plan_service.revise_plan(
        MagicMock(),
        7,
        TripPlanReviseRequest(
            revision_request="减少步行",
        ),
        user_id=1,
    )

    assert result is request
    assert workflow_inputs[0].trip_id == 42
