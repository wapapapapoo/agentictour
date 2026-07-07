from schemas.trip_plan import TripPlanGenerateRequest
from services import trip_plan_service


def test_to_dify_inputs_keeps_all_values_as_strings() -> None:
    request = TripPlanGenerateRequest(
        action="create",
        user_id="test-user-001",
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

    inputs = trip_plan_service._to_dify_inputs(request)

    assert inputs == {
        "action": "create",
        "user_id": "test-user-001",
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
