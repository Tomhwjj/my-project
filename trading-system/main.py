"""交易系统 — 启动入口"""
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from journal.routes import router
from journal.models import init_db
import os

app = FastAPI(title="Trading System", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


@app.on_event("startup")
def startup():
    init_db()
    print("✅ Trading System — http://localhost:8765")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
