import json
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analyze import analyze

app = FastAPI(title="AI Behavioral Bias Auditor")

# lets the website (running on another port) talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data/uploads", exist_ok=True)


@app.get("/")
def home():
    return {"message": "Bias Auditor API is running"}


@app.get("/samples")
def list_samples():
    """Names of the built-in demo traders."""
    return sorted(f for f in os.listdir("data/synthetic") if f.endswith(".csv"))


@app.get("/analyze-sample/{name}")
def analyze_sample(name: str):
    """Analyze one of the demo files (for the 'Try with sample data' button)."""
    path = os.path.join("data/synthetic", os.path.basename(name))
    if not os.path.exists(path):
        raise HTTPException(404, "Sample not found")
    return json.loads(json.dumps(analyze(path), default=float))


@app.post("/analyze")
async def analyze_upload(file: UploadFile = File(...)):
    """Analyze a CSV uploaded by the user."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")

    path = f"data/uploads/{uuid.uuid4().hex}.csv"
    with open(path, "wb") as f:
        f.write(await file.read())
    try:
        result = analyze(path)
        result["file"] = file.filename
        return json.loads(json.dumps(result, default=float))
    except Exception:
        raise HTTPException(400, "Could not read this file. Check that it is a Zerodha tradebook.")
    finally:
        os.remove(path)  # privacy: delete the uploaded file right after analysis