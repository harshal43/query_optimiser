from backend.agents.advisor import parse_human_flags, parse_suggestions


def test_parse_human_flags_returns_empty_when_no_section():
    raw = "SUGGESTIONS:\n1. Add index\n   Explanation: faster lookup\n   Snowflake Note: N/A"
    assert parse_human_flags(raw) == []


def test_parse_human_flags_single_flag():
    raw = (
        "SUGGESTIONS:\n"
        "1. Add index\n"
        "   Explanation: faster\n"
        "   Snowflake Note: N/A\n"
        "\n"
        "HUMAN_FLAGS:\n"
        "HF_ID: hf_1\n"
        "HF_TYPE: select_star\n"
        "HF_TITLE: SELECT * detected\n"
        "HF_DESCRIPTION: Cannot prune without column list\n"
        "HF_PLACEHOLDER: Enter columns e.g. ORDER_ID, STATUS\n"
        "HF_SNIPPET: SELECT * FROM orders\n"
    )
    flags = parse_human_flags(raw)
    assert len(flags) == 1
    assert flags[0] == {
        "id": "hf_1",
        "type": "select_star",
        "title": "SELECT * detected",
        "description": "Cannot prune without column list",
        "placeholder": "Enter columns e.g. ORDER_ID, STATUS",
        "sql_snippet": "SELECT * FROM orders",
    }


def test_parse_human_flags_two_flags():
    raw = (
        "SUGGESTIONS:\n"
        "1. Add index\n\n"
        "HUMAN_FLAGS:\n"
        "HF_ID: hf_1\n"
        "HF_TYPE: select_star\n"
        "HF_TITLE: Title 1\n"
        "HF_DESCRIPTION: Desc 1\n"
        "HF_PLACEHOLDER: Place 1\n"
        "HF_SNIPPET: SELECT * FROM t1\n"
        "\n"
        "HF_ID: hf_2\n"
        "HF_TYPE: missing_filter\n"
        "HF_TITLE: Title 2\n"
        "HF_DESCRIPTION: Desc 2\n"
        "HF_PLACEHOLDER: Place 2\n"
        "HF_SNIPPET: SELECT id FROM t2\n"
    )
    flags = parse_human_flags(raw)
    assert len(flags) == 2
    assert flags[0]["id"] == "hf_1"
    assert flags[1]["id"] == "hf_2"
    assert flags[1]["type"] == "missing_filter"


def test_parse_human_flags_missing_optional_fields():
    raw = "HUMAN_FLAGS:\nHF_ID: hf_1\n"
    flags = parse_human_flags(raw)
    assert len(flags) == 1
    assert flags[0]["id"] == "hf_1"
    assert flags[0]["type"] == ""
    assert flags[0]["title"] == ""


def test_parse_human_flags_case_insensitive_section_header():
    raw = "human_flags:\nHF_ID: hf_1\nHF_TYPE: select_star\n"
    flags = parse_human_flags(raw)
    assert len(flags) == 1
    assert flags[0]["type"] == "select_star"
