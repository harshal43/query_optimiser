import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize("priority,tolerance,expected_tier", [
    ("cost_savings", "minimal",  "conservative"),
    ("cost_savings", "standard", "conservative"),
    ("cost_savings", "major",    "balanced"),
    ("balanced",     "minimal",  "conservative"),
    ("balanced",     "standard", "balanced"),
    ("balanced",     "major",    "aggressive"),
    ("speed",        "minimal",  "balanced"),
    ("speed",        "standard", "aggressive"),
    ("speed",        "major",    "aggressive"),
])
def test_qualify_matrix(priority, tolerance, expected_tier):
    res = client.post("/api/qualify", json={"priority": priority, "tolerance": tolerance})
    assert res.status_code == 200
    data = res.json()
    assert data["recommended_tier"] == expected_tier
    assert "rules_preview" in data


def test_qualify_rules_preview_contains_advisor_and_optimizer():
    res = client.post("/api/qualify", json={"priority": "balanced", "tolerance": "standard"})
    assert res.status_code == 200
    preview = res.json()["rules_preview"]
    assert "advisor_rules" in preview
    assert "optimizer_rules" in preview


def test_qualify_invalid_priority_returns_422():
    res = client.post("/api/qualify", json={"priority": "invalid", "tolerance": "minimal"})
    assert res.status_code == 422


def test_qualify_invalid_tolerance_returns_422():
    res = client.post("/api/qualify", json={"priority": "speed", "tolerance": "invalid"})
    assert res.status_code == 422


def test_qualify_missing_fields_returns_422():
    res = client.post("/api/qualify", json={"priority": "speed"})
    assert res.status_code == 422
