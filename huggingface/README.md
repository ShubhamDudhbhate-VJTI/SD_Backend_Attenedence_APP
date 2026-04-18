---
title: AttendX AI Verification
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# AttendX Face Verification Service

This is the AI microservice for the **AttendX Attendance System**. 
It handles face embedding extraction and verification using **DeepFace (VGG-Face)**.

## API Endpoints

- `GET /`: Health check.
- `POST /represent`: Takes an image and returns a 4096-d embedding.
- `POST /verify`: Takes an image and a stored embedding, returns match status.

## Technologies
- FastAPI
- DeepFace
- OpenCV
- TensorFlow (VGG-Face)
