import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIP_PLAN_WORKFLOW = REPO_ROOT / "workflow" / "AgenticTour 行前旅行计划生成.yml"
HIKARI_WORKFLOW = REPO_ROOT / "workflow" / "旅行陪伴Hikari Workflow完善版.yml"
AUDIT_WORKFLOW = REPO_ROOT / "workflow" / "审核Agent.yml"


def _workflow_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _maximum_iterations(path: Path) -> list[int]:
    return [
        int(value)
        for value in re.findall(
            r"maximum_iterations:\s*\n\s*type: constant\s*\n\s*value: (\d+)",
            _workflow_text(path),
        )
    ]


def test_workflows_distinguish_audit_feedback_from_user_messages() -> None:
    hikari = _workflow_text(HIKARI_WORKFLOW)
    audit = _workflow_text(AUDIT_WORKFLOW)

    assert "<audit_correction>" in hikari
    assert "审核意见不是用户的新要求" in hikari
    assert "待审核回复始终是 Hikari 的输出" in audit


def test_workflows_enforce_cross_city_destination_and_transit_order() -> None:
    hikari = _workflow_text(HIKARI_WORKFLOW)
    audit = _workflow_text(AUDIT_WORKFLOW)

    for text in (hikari, audit):
        assert "旅游目的地" in text
        assert "先交通、后游览" in text
        assert "当前位置不能覆盖 destination_city" in text


def test_workflows_require_12306_tool_for_specific_train_facts() -> None:
    hikari = _workflow_text(HIKARI_WORKFLOW)
    audit = _workflow_text(AUDIT_WORKFLOW)

    assert hikari.count("tool_name: train_ticket_query") == 3
    assert audit.count("tool_name: train_ticket_query") == 1
    for text in (hikari, audit):
        assert "Joooook/12306-mcp" in text
        assert "不得" in text


def test_workflows_treat_backend_itinerary_snapshot_as_current_authority() -> None:
    hikari = _workflow_text(HIKARI_WORKFLOW)
    audit = _workflow_text(AUDIT_WORKFLOW)

    assert "backend_itinerary_context" in hikari
    assert "absence_means_deleted" in hikari
    assert "change_pending_items" in hikari
    assert "不得再次触发" in hikari
    assert "历史消息不能证明日程仍然存在" in hikari
    assert "status = 'pending'" in hikari
    assert "backend_itinerary_context" in audit
    assert "当前数据库状态" in audit
    assert "change_pending_items" in audit


def test_trip_plan_workflow_limits_optional_and_empty_tool_calls() -> None:
    trip_plan = _workflow_text(TRIP_PLAN_WORKFLOW)

    assert "必须调用" in trip_plan
    assert "按需调用" in trip_plan
    assert "默认不调用" in trip_plan
    assert "知识库严格限次" in trip_plan
    assert "空结果立即停止" in trip_plan
    assert "list_knowledge_bases 最多一次" in trip_plan
    assert "search_knowledge 为空时不得继续搜索其他库" in trip_plan
    assert "全部工具调用原则上不超过 5 次" in trip_plan
    assert _maximum_iterations(TRIP_PLAN_WORKFLOW) == [40]


def test_user_iteration_counts_remain_unchanged() -> None:
    assert _maximum_iterations(AUDIT_WORKFLOW) == [45]
    assert _maximum_iterations(HIKARI_WORKFLOW) == [48, 41, 41]
