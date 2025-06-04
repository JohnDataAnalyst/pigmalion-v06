# backend/main.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analyse.analyse_post_unitaire import analyser_post

# Charge le fichier `.env10` situé dans le même dossier que main.py
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env10"))

app = FastAPI(title="API Pigmalion - Analyse Bluesky")

# Autoriser CORS depuis localhost:3000 (React) ou 8501 (Streamlit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1"}

@app.get("/analyze")
async def analyze(url: str):
    """
    Appel : GET /analyze?url=https://bsky.app/...
    Retourne un dict JSON issu de analyser_post() ou une erreur 400.
    """
    result = analyser_post(url)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
