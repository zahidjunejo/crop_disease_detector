---
title: Crop Disease Detector
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# 🌿 AI Crop Disease Detector

AI-powered crop disease diagnosis from a single photo — with treatment guidance in English and Urdu.

## What This Project Does

Upload a photo of a diseased crop leaf and receive:
- The name of the disease
- A confidence score (how sure the AI is)
- Severity level (Low / Medium / High)
- Treatment steps in English and Urdu
- Recommended pesticide
- Prevention tips

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| AI Model | Meta LLaMA 4 Scout (Vision) via Groq API |
| Deployment | Hugging Face Spaces (Docker) |

## How the AI Works

The app uses meta-llama/llama-4-scout-17b-16e-instruct — a large language model with vision capabilities, meaning it can understand both text and images.

### The Vision Pipeline

1. Farmer uploads a leaf image via the browser
2. Frontend sends the image to the FastAPI backend
3. Backend encodes the image as Base64
4. Backend sends the image + prompt to Groq API
5. LLaMA 4 Scout analyzes the image and returns JSON
6. Backend parses the response and returns results to the farmer

### The Prompt

The model is instructed to return only valid JSON with keys: disease_name, confidence_percent, treatment_english, treatment_urdu, pesticide, prevention_tips.

### Confidence Score

Returned by the model (0-100) and mapped to severity:
- 80-100 → High
- 50-79 → Medium
- 0-49 → Low

## Project Structure

text
crop-disease-detector/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── Dockerfile
├── .env
└── README.md


Setup
	1.	Install dependencies:

pip install -r backend/requirements.txt


	2.	Add your Groq key to .env:

GROQ_API_KEY=your_key_here


	3.	Run the app:

python backend/main.py


	4.	Open: http://127.0.0.1:7860
API Endpoints



|Endpoint|Method|Description                     |
|--------|------|--------------------------------|
|/       |GET   |Serves the frontend             |
|/health |GET   |Checks server and API key       |
|/analyze|POST  |Accepts image, returns diagnosis|

Built By
Zahid Junejo — AI Student, Pakistan
Powered by Groq Vision · Meta LLaMA 4 Scout · FastAPI
