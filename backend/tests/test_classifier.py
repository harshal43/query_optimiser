from __future__ import annotations
from app.services.classifier import classify


def test_spilling_critical():
    cl, sev, issue = classify("SELECT * FROM t", {"bytes_spilled_remote": 50_000_000})
    assert cl == "spilling"
    assert sev == "critical"


def test_spilling_high():
    cl, sev, issue = classify("SELECT * FROM t", {"bytes_spilled_remote": 1_000_000})
    assert cl == "spilling"
    assert sev == "high"


def test_scan_heavy():
    cl, sev, issue = classify("SELECT * FROM t", {"bytes_scanned": 1_000_000, "rows_produced": 10, "credits_used": 10})
    assert cl == "scan-heavy"


def test_join_inefficient():
    sql = "SELECT * FROM a JOIN b ON a.id=b.id JOIN c ON c.id=b.id JOIN d ON d.id=c.id JOIN e ON e.id=d.id"
    cl, sev, issue = classify(sql, {"execution_time_ms": 5000})
    assert cl == "join-inefficient"


def test_repeated_pattern():
    cl, sev, issue = classify("SELECT id FROM users WHERE id = 1", {"execution_time_ms": 100, "credits_used": 0.2})
    assert cl == "repeated-pattern"
    assert sev == "low"


def test_no_issues():
    cl, sev, issue = classify("SELECT 1", {})
    assert sev == "low"
