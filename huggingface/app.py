import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from deepface import DeepFace
import numpy as np
import json
import tempfile
import time

app = FastAPI()

# Global model warm-up flag
MODELS_LOADED = False

def warm_up_models():
    """Warms up DeepFace models on startup to avoid delay on first request."""
    global MODELS_LOADED
    try:
        print("--- WARMING UP AI MODELS (VGG-Face + MTCNN) ---")
        # Creating a dummy image to trigger model loading
        img = np.zeros((224, 224, 3), dtype=np.uint8)
        DeepFace.represent(img, model_name="VGG-Face", detector_backend="mtcnn", enforce_detection=False)
        MODELS_LOADED = True
        print("--- AI MODELS READY ---")
    except Exception as e:
        print(f"--- WARMUP ERROR: {e} ---")

@app.on_event("startup")
async def startup_event():
    warm_up_models()

@app.get("/")
def read_root():
    return {
        "status": "AI Verification Server Online",
        "models_ready": MODELS_LOADED,
        "model": "VGG-Face",
        "detector": "mtcnn"
    }

@app.post("/verify")
async def verify_face(
    image: UploadFile = File(...),
    stored_embedding: str = Form(...) # JSON string of the embedding
):
    try:
        # Save uploaded image to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await image.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Extract embedding from the current image
            # enforce_detection=False allows processing even if face is slightly obscured
            objs = DeepFace.represent(
                img_path=tmp_path,
                model_name="VGG-Face",
                detector_backend="mtcnn",
                enforce_detection=False
            )

            if not objs or len(objs) == 0:
                return {"success": False, "error": "No face detected. Please ensure your face is clear."}

            current_emb = np.array(objs[0]["embedding"])
            stored_emb = np.array(json.loads(stored_embedding))

            # Calculate Cosine Distance
            dot_product = np.dot(current_emb, stored_emb)
            norm_current = np.linalg.norm(current_emb)
            norm_stored = np.linalg.norm(stored_emb)

            # Avoid division by zero
            if norm_current == 0 or norm_stored == 0:
                return {"success": False, "error": "Invalid embedding vector"}

            cosine_similarity = dot_product / (norm_current * norm_stored)
            dist = 1 - cosine_similarity

            # Threshold for VGG-Face is typically 0.40, using 0.45 for better real-world matching
            threshold = 0.40
            is_match = float(dist) < threshold

            return {
                "success": True,
                "is_match": is_match,
                "distance": float(dist),
                "threshold": threshold
            }

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        print(f"Verify Error: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/represent")
async def represent_face(image: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await image.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            objs = DeepFace.represent(
                img_path=tmp_path,
                model_name="VGG-Face",
                detector_backend="mtcnn",
                enforce_detection=True # We want clear face during registration
            )

            if not objs or len(objs) == 0:
                return {"success": False, "error": "No face detected during registration."}

            return {
                "success": True,
                "embedding": objs[0]["embedding"]
            }

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        print(f"Represent Error: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
