from __future__ import annotations

import json

from app.provider_adapters import _strict_provider_schema
from app.schemas import ModelInterpretation


UNSUPPORTED_STRICT_SCHEMA_KEYS = {
    "default",
    "description",
    "examples",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "format",
    "maxItems",
    "maxLength",
    "maxProperties",
    "maximum",
    "minItems",
    "minLength",
    "minProperties",
    "minimum",
    "multipleOf",
    "pattern",
    "title",
    "uniqueItems",
}


def _walk(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_model_interpretation_strict_schema_strips_provider_rejected_keywords() -> None:
    schema = _strict_provider_schema(ModelInterpretation.model_json_schema())

    for node in _walk(schema):
        assert UNSUPPORTED_STRICT_SCHEMA_KEYS.isdisjoint(node)


def test_model_interpretation_strict_schema_requires_all_object_fields() -> None:
    schema = _strict_provider_schema(ModelInterpretation.model_json_schema())

    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "language",
        "intent",
        "unauthorized_activity_asserted",
        "transaction_id",
        "transaction_query",
    ]
    transaction_query = schema["$defs"]["InterpretedTransactionQuery"]
    assert transaction_query["additionalProperties"] is False
    assert transaction_query["required"] == [
        "date_from",
        "date_to",
        "amount",
        "transaction_type",
        "status",
    ]


def test_model_interpretation_strict_schema_keeps_enum_and_nullability_contract() -> None:
    schema = _strict_provider_schema(ModelInterpretation.model_json_schema())
    serialized = json.dumps(schema, sort_keys=True)

    assert "SupportedLanguage" in serialized
    assert "transaction_lookup" in serialized
    assert "unauthorized_activity_asserted" in serialized
    assert '"type": "null"' in serialized
    assert "TransactionTypeFilter" in serialized
    assert "TransactionStatusFilter" in serialized
