FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for Manim + OCR
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    ffmpeg \
    git \
    curl \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    texlive \
    texlive-latex-extra \
    texlive-fonts-extra \
    dvisvgm \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY .env.docker .env

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]