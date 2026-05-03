# AI Crop Disease Detector

An agriculture-focused web app for Pakistani farmers:
- Upload a crop image
- Detect likely disease with an AI vision model
- Get treatment guidance in English and Urdu
- See pesticide and prevention recommendations

## Tech Stack

- Backend: FastAPI
- Disease classifier: Hugging Face model `linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification`
- LLM recommendations: Groq `llama-3.1-8b-instant`
- Vision fallback: Groq `llama-3.2-11b-vision-preview`
- Frontend: single `index.html` (no separate CSS/JS files)

## Project Structure

```text
crop-disease-detector/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── .env
├── Procfile
├── render.yaml
└── README.md
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Add your Groq key to `.env`:
   ```env
   GROQ_API_KEY=your_key_here
   ```
3. Run the app:
   ```bash
   uvicorn main:app --reload --port 8000 --app-dir .\backend
   ```
4. Open:
   - `http://127.0.0.1:8000`

## API

### `POST /analyze`

Upload multipart image with form key `file`.

Returns:
- `disease_name`
- `confidence`
- `severity` (Low/Medium/High)
- `treatment_english`
- `treatment_urdu`
- `pesticide`
- `prevention_tips`
- `diagnosis_source`
- `recommendation_source`

## Reliability / Fallback Strategy

The API is designed to always return useful output:
1. Try Hugging Face plant disease model
2. If that fails, try Groq vision diagnosis
3. If that fails, use built-in disease mapping fallback
4. For recommendations, try Groq text model; if unavailable, use local bilingual fallback guidance

## Render Deployment

- `Procfile` and `render.yaml` are included
- Set `GROQ_API_KEY` in Render environment variables
