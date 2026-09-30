import importlib
import json

import config
from core import mock_feed
from core.alert_store import AlertStore
from core.schema import flatten, validate_alert


def test_mock_alerts_match_schema():
    for _ in range(200):
        a = validate_alert(mock_feed.generate_alert())
        assert a is not None and a["severity"] in config.SEVERITY_ORDER
        assert 0 <= a["confidence_score"] <= 1
        flatten(a)


def test_sample_alert_valid():
    raw = json.loads((config.BASE_DIR / "data" / "sample_alert.json").read_text())
    assert validate_alert(raw)["alert_id"] == "ALT-20260929-1094"


def test_rejects_malformed():
    assert validate_alert({"alert_id": "x"}) is None
    assert validate_alert("nope") is None


def test_vigilant_env_names_supported(monkeypatch):
    monkeypatch.setenv("VIGILANT_MODE", "file")
    monkeypatch.setenv("VIGILANT_ALERTS_FILE", "/tmp/vigilant-alerts.jsonl")
    monkeypatch.setenv("VIGILANT_TELEMETRY_FILE", "/tmp/vigilant-telemetry.json")
    monkeypatch.setenv("VIGILANT_REFRESH", "2.5")
    importlib.reload(config)

    assert config.DATA_MODE == "file"
    assert str(config.ALERTS_FILE) == "/tmp/vigilant-alerts.jsonl"
    assert str(config.TELEMETRY_FILE) == "/tmp/vigilant-telemetry.json"
    assert config.REFRESH_SECONDS == 2.5

    monkeypatch.delenv("VIGILANT_MODE", raising=False)
    monkeypatch.delenv("VIGILANT_ALERTS_FILE", raising=False)
    monkeypatch.delenv("VIGILANT_TELEMETRY_FILE", raising=False)
    monkeypatch.delenv("VIGILANT_REFRESH", raising=False)
    importlib.reload(config)


def test_file_tail(tmp_path, monkeypatch):
    p = tmp_path / "alerts.jsonl"
    monkeypatch.setattr(config, "ALERTS_FILE", p)
    monkeypatch.setattr(config, "TELEMETRY_FILE", tmp_path / "t.json")
    store = AlertStore(mode="file")
    p.write_text(json.dumps(mock_feed.generate_alert()) + "\nnot json\n")
    store.poll()
    assert len(store.alerts) == 1 and store.rejected == 1
    with open(p, "a") as fh:
        fh.write(json.dumps(mock_feed.generate_alert()) + "\n")
    store.poll()
    assert len(store.alerts) == 2
