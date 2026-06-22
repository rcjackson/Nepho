"""Offline tests for DQ response parsing."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dq_pipeline import parse_dq_response


def test_parse_clean_json():
    text = ('{"issues_found": true, "severity": "Bad", '
            '"summary": "Flat-lined data.", "issues": ["temp stuck at 0"]}')
    result = parse_dq_response(text)
    assert result["issues_found"] is True
    assert result["severity"] == "Bad"
    assert result["summary"] == "Flat-lined data."
    assert result["issues"] == ["temp stuck at 0"]


def test_parse_fenced_json():
    text = ('```json\n{"issues_found": false, "severity": "Good", '
            '"summary": "Looks good.", "issues": []}\n```')
    result = parse_dq_response(text)
    assert result["issues_found"] is False
    assert result["severity"] == "Good"
    assert result["summary"] == "Looks good."
    assert result["issues"] == []


def test_parse_json_in_prose():
    text = ('Here is my assessment:\n'
            '{"issues_found": true, "severity": "Indeterminate", '
            '"summary": "Minor noise.", "issues": ["slight noise"]} '
            'Hope that helps!')
    result = parse_dq_response(text)
    assert result["issues_found"] is True
    assert result["severity"] == "Indeterminate"
    assert result["issues"] == ["slight noise"]


def test_parse_severity_canonicalized_case_insensitively():
    text = '{"issues_found": false, "severity": "good", "summary": "x", "issues": []}'
    result = parse_dq_response(text)
    assert result["severity"] == "Good"  # lowercase input -> canonical form


def test_parse_garbage_falls_back():
    text = "I could not analyze the images, sorry."
    result = parse_dq_response(text)
    assert result["issues_found"] is None
    assert result["severity"] is None
    assert result["summary"] == "I could not analyze the images, sorry."
    assert result["issues"] == []


def test_parse_empty_falls_back():
    result = parse_dq_response("")
    assert result["issues_found"] is None
    assert result["summary"] == ""


def test_parse_invalid_severity_nulled():
    text = '{"issues_found": true, "severity": "catastrophic", "summary": "x", "issues": []}'
    result = parse_dq_response(text)
    assert result["issues_found"] is True
    assert result["severity"] is None  # not in the allowed set


def test_parse_non_bool_issues_found_nulled():
    text = '{"issues_found": "yes", "severity": "low", "summary": "x", "issues": []}'
    result = parse_dq_response(text)
    assert result["issues_found"] is None


def test_parse_nested_braces_in_summary():
    text = '{"issues_found": false, "severity": "none", "summary": "range {0,1}", "issues": []}'
    result = parse_dq_response(text)
    assert result["issues_found"] is False
    assert result["summary"] == "range {0,1}"
