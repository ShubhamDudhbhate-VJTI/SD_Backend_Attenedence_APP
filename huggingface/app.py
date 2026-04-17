import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from deepface import DeepFace
import numpy as np
import json
import tempfile
import time

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "AI Verification Server Online", "model": "VGG-Face", "detector": "mtcnn"}

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
            objs = DeepFace.represent(
                img_path=tmp_path,
                model_name="VGG-Face",
                detector_backend="mtcnn",
                enforce_detection=True
            )

            if not objs:
                return {"success": False, "error": "No face detected"}

            current_emb = np.array(objs[0]["embedding"])
            stored_emb = np.array(json.loads(stored_embedding))

            # Calculate Cosine Distance
            dot_product = np.dot(current_emb, stored_emb)
            norm_current = np.linalg.norm(current_emb)
            norm_stored = np.linalg.norm(stored_emb)
            cosine_similarity = dot_product / (norm_current * norm_stored)
            dist = 1 - cosine_similarity

            # Threshold for VGG-Face is 0.40
            is_match = float(dist) < 0.40

            return {
                "success": True,
                "is_match": is_match,
                "distance": float(dist),
                "threshold": 0.40
            }

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
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
                enforce_detection=True
            )

            if not objs:
                return {"success": False, "error": "No face detected"}

            return {
                "success": True,
                "embedding": objs[0]["embedding"]
            }

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
