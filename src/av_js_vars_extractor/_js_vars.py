import enum
import json
import logging
from collections.abc import Iterator
from typing import Any

import chompjs
import esprima
from esprima import Error
from esprima.nodes import ExpressionStatement, Node, VariableDeclaration
from selectolax.lexbor import LexborHTMLParser

logger = logging.getLogger(__name__)


class StatementType(enum.StrEnum):
    EXPRESSION_STATEMENT = "ExpressionStatement"
    VARIABLE_DECLARATION = "VariableDeclaration"
    FUNCTION_DECLARATION = "FunctionDeclaration"
    CLASS_DECLARATION = "ClassDeclaration"


class ExpressionType(enum.StrEnum):
    LITERAL = "Literal"
    OBJECT_EXPRESSION = "ObjectExpression"
    ARRAY_EXPRESSION = "ArrayExpression"

    MEMBER_EXPRESSION = "MemberExpression"  # window.CONFIG, obj['prop']
    UNARY_EXPRESSION = "UnaryExpression"  # -100, !true, void 0
    BINARY_EXPRESSION = "BinaryExpression"  # "a" + "b", 10 + 20
    IDENTIFIER = "Identifier"  # undefined, NaN, configVar
    CALL_EXPRESSION = "CallExpression"  # JSON.parse("...")
    TEMPLATE_LITERAL = "TemplateLiteral"  # `template_string`
    LOGICAL_EXPRESSION = "LogicalExpression"  # a || b
    CONDITIONAL_EXPRESSION = "ConditionalExpression"  # a ? b : c


def _extract_var_name(left: Node) -> str | None:
    if left.type == ExpressionType.MEMBER_EXPRESSION:
        obj_name = (
            left.object.name
            if left.object.type == ExpressionType.IDENTIFIER
            else ""
        )
        prop_name = (
            left.property.name
            if left.property.type == ExpressionType.IDENTIFIER
            else ""
        )
        return f"{obj_name}.{prop_name}" if obj_name else prop_name
    elif left.type == ExpressionType.IDENTIFIER:
        return left.name
    return None


def _extract_var_value(
    expr,
    script_text: str,
) -> int | float | str | dict | list | None:
    if expr.type == ExpressionType.LITERAL:
        if isinstance(expr.value, str):
            try:
                return json.loads(expr.value)
            except json.JSONDecodeError:
                pass
        return expr.value
    elif expr.type in (
        ExpressionType.OBJECT_EXPRESSION,
        ExpressionType.ARRAY_EXPRESSION,
    ):
        text = script_text[expr.range[0] : expr.range[1]]  # noqa: E203
        value = chompjs.parse_js_object(text)
        return value
    return None


def _parse_assignment(
    statement: ExpressionStatement,
    scrtipt_text: str,
    data: dict[str, object],
) -> None:
    expr = statement.expression
    if expr.left and (var_name := _extract_var_name(expr.left)):
        if expr.right.type == ExpressionType.LITERAL:
            data[var_name] = _extract_var_value(expr.right, scrtipt_text)


def _parse_variable_declaration(
    statement: VariableDeclaration,
    script_text: str,
    data: dict[str, object],
) -> None:
    for decl in statement.declarations:
        if decl.init:
            data[decl.id.name] = _extract_var_value(decl.init, script_text)


def extract_js_vars(script_text: str) -> dict[str, object]:
    data: dict[str, object] = {}
    ast = esprima.parseScript(script_text, {"tolerant": True, "range": True})
    for statement in ast.body:
        if statement.type == StatementType.EXPRESSION_STATEMENT:
            _parse_assignment(statement, script_text, data)
        elif statement.type == StatementType.VARIABLE_DECLARATION:
            _parse_variable_declaration(statement, script_text, data)
    return data


def js_vars_iter(parser: LexborHTMLParser) -> Iterator[dict[str, object]]:
    for script_el in parser.css("script:not([type='application/ld+json'])"):
        if text := script_el.text():
            try:
                if script_data := extract_js_vars(text):
                    yield script_data
            except Error as e:
                logger.warning("%s %s", type(e), e)


def find_js_var(var_name: str, parser: LexborHTMLParser) -> Any | None:
    for variables in js_vars_iter(parser):
        if var_name in variables:
            return variables[var_name]
    return None
