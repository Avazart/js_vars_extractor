import logging
from typing import Any

import pytest
from selectolax.lexbor import LexborHTMLParser

from av_js_vars_extractor import extract_js_vars, find_js_var, js_vars_iter


@pytest.fixture
def html_document() -> str:
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <script type="application/ld+json">
                {"@context": "https://schema.org", "ignoredKey": 
                "should_not_be_extracted"}
            </script>
            <script>
                var siteConfig = { theme: "dark", version: 2 };
            </script>
        </head>
        <body>
            <script>
                window.USER_ID = 555;
                var broken = { unclosed: ;
            </script>
        </body>
    </html>
    """


def test_extract_var_name_from_real_ast() -> None:
    script_id = "var myVar = 10;"
    vars_id = extract_js_vars(script_id)
    assert "myVar" in vars_id

    script_member = 'window.CONFIG = "production";'
    vars_member = extract_js_vars(script_member)
    assert "window.CONFIG" in vars_member


def test_extract_js_vars_primitives_and_structures() -> None:
    script = """
    var integerVal = 42;
    var floatVal = 3.14;
    var boolVal = true;
    var strVal = "hello world";
    var jsonStrVal = '{"nested": "data", "count": 5}';
    var rawObj = { a: 1, b: [2, 3] };
    var rawArr = ["apple", "banana"];
    """
    data = extract_js_vars(script)

    assert data["integerVal"] == 42
    assert data["floatVal"] == 3.14
    assert data["strVal"] == "hello world"
    assert data["jsonStrVal"] == {"nested": "data", "count": 5}
    assert data["rawObj"] == {"a": 1, "b": [2, 3]}
    assert data["rawArr"] == ["apple", "banana"]


def test_js_vars_iter_filters_ld_json_and_handles_syntax_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <script type="application/ld+json">
                {"@context": "https://schema.org", "ignored": true}
            </script>
            <script>
                var siteConfig = { theme: "dark" };
            </script>
        </head>
        <body>
            <script>
                var broken = { unclosed: ;
            </script>
            <script>
                window.USER_ID = 555;
            </script>
        </body>
    </html>
    """
    parser = LexborHTMLParser(html)

    with caplog.at_level(logging.WARNING):
        results = list(js_vars_iter(parser))

    assert results == [
        {"siteConfig": {"theme": "dark"}},
        {"window.USER_ID": 555},
    ]

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "Error" in caplog.text


def test_find_js_var_returns_first_matching_occurrence() -> None:
    html = """
    <script>var APP_STATUS = "first";</script>
    <script>var APP_STATUS = "second";</script>
    """
    parser = LexborHTMLParser(html)
    assert find_js_var("APP_STATUS", parser) == "first"


def test_find_js_var_continues_searching_after_js_syntax_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    html = """
    <script>var broken = {;</script>
    <script>var validVar = 100;</script>
    """
    parser = LexborHTMLParser(html)

    with caplog.at_level(logging.WARNING):
        assert find_js_var("validVar", parser) == 100

    assert any(
        "esprima" in record.message.lower() for record in caplog.records
    )


def test_find_js_var_handles_empty_and_external_scripts() -> None:
    html = """
    <script src="https://example.com/app.js"></script>
    <script></script>
    <script>   \n   </script>
    <script>var target = true;</script>
    """
    parser = LexborHTMLParser(html)
    assert find_js_var("target", parser) is True


@pytest.mark.parametrize(
    ("html", "var_name", "expected"),
    [
        ("<script>const a = [1, 2, 3];</script>", "a", [1, 2, 3]),
        ("<script>let b = null;</script>", "b", None),
        (
            "<script>window.IS_ADMIN = false;</script>",
            "window.IS_ADMIN",
            False,
        ),
        ('<script type="application/ld+json">{"a": 1}</script>', "a", None),
    ],
)
def test_find_js_var_edge_cases_and_types(
    html: str,
    var_name: str,
    expected: Any,
) -> None:
    parser = LexborHTMLParser(html)
    assert find_js_var(var_name, parser) == expected
