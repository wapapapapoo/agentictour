import pytest

from travel_mcp import configs


def test_check_settings_requires_amap_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(configs.settings, "AMAP_KEY", "")

    with pytest.raises(RuntimeError, match="AMAP_KEY"):
        configs.check_settings()


def test_check_settings_accepts_amap_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(configs.settings, "AMAP_KEY", "test-key")

    configs.check_settings()
