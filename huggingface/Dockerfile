# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Create a non-root user for security (required by Hugging Face)
RUN useradd -m -u 1000 user
USER user
# Set environment variables for TensorFlow stability and cleaner logs
ENV TF_ENABLE_ONEDNN_OPTS=0
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV PATH="/home/user/.local/bin:$PATH"

# Copy requirements and install dependencies
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Pre-download the VGG-Face model and MTCNN detector weights
RUN python -c "from deepface import DeepFace; DeepFace.build_model('VGG-Face')"
RUN python -c "import numpy as np; from deepface import DeepFace; img = np.zeros((224,224,3), dtype=np.uint8); DeepFace.represent(img, model_name='VGG-Face', detector_backend='mtcnn', enforce_detection=False)"

# Copy the rest of the application
COPY --chown=user . /app

# Expose the port FastAPI will run on
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
