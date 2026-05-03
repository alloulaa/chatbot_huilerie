from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.chat_controller import router as chat_router

load_dotenv()

app = FastAPI(title="Chatbot Huilerie - Prototype enrichi", version="2.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/")
def index():
	return {"status": "ok", "message": "Chatbot Huilerie - interface static disabled"}


@app.get("/health")
def health():
	return {"status": "ok"}
