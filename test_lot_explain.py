#!/usr/bin/env python3
from app.models import ChatRequest
from app.controllers.chat_controller import ask_chatbot

payload = ChatRequest(
    message="Pourquoi le lot LO16 a une mauvaise qualité ?",
    user_id=1,
    session_id="test-session-2",
)

resp = ask_chatbot(payload)
print("=== ask_chatbot response ===")
print(f"type: {resp.type}")
print(f"intent: {resp.intent}")
print(f"message: {resp.message}")
print(f"pending_choice: {resp.pending_choice}")
print(f"options: {resp.options}")
print(f"response: {resp.response}")
print(f"data keys: {list(resp.data.keys()) if isinstance(resp.data, dict) else type(resp.data)}")
