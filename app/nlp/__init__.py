"""NLP package with compatibility aliases for legacy imports."""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from typing import Any

from app.nlp.factory import NLPFactory


async def analyser_message(message: str) -> dict[str, Any]:
	"""Analyse a message with the active NLP implementation."""
	result = await NLPFactory.get_instance().analyze(message)
	return result._asdict()


def analyser_message_sync(message: str) -> dict[str, Any]:
	"""Synchronous compatibility wrapper for legacy callers."""
	try:
		asyncio.get_running_loop()
	except RuntimeError:
		return asyncio.run(analyser_message(message))

	raise RuntimeError(
		"analyser_message_sync ne peut pas être appelé depuis une boucle asyncio active. "
		"Utilisez analyser_message à la place."
	)


_legacy_module = ModuleType("app.nlp.analyseur_llm")
_legacy_module.analyser_message = analyser_message
_legacy_module.analyser_message_sync = analyser_message_sync
sys.modules.setdefault("app.nlp.analyseur_llm", _legacy_module)
