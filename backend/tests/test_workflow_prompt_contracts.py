import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
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


def test_user_iteration_counts_remain_unchanged() -> None:
    assert _maximum_iterations(AUDIT_WORKFLOW) == [45]
    assert _maximum_iterations(HIKARI_WORKFLOW) == [48, 41, 41]
