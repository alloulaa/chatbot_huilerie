"""Helpers purs pour structurer les réponses du chat."""

from app.utils.shared import (
    fmt_number,
    is_chart_request,
    normalize_choice,
    safe_float,
    scope_text,
)

_safe_float = safe_float
_fmt = fmt_number
_scope = scope_text
_is_chart_request = is_chart_request
_normalize_choice = normalize_choice


def build_chat_response(*args, **kwargs):
    from app.services.response_builder import (
        build_chat_response as _build_chat_response,
    )

    return _build_chat_response(*args, **kwargs)
