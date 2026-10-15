# PDF Summarizer and Chatbot using LLaMa2 (v2)

![Screenshot (481)](https://github.com/user-attachments/assets/f5c8a6d0-e9db-4113-a6d2-a44e478b0845)

## Project Overview
The PDF Summarizer & Chatbot is a Streamlit web app that lets you upload one or more PDFs and either generate an AI summary or chat with the document using Llama models served by Replicate. It extracts text with `pypdf`, supports OCR fallback for scanned PDFs, and provides multi-PDF management, citations, and export.

## Features (v2)
- **Multi-PDF library**: upload many PDFs, switch between them, remove individual ones, with page/word metadata.
- **One-click summarization**: choose format (paragraph / bullet / executive), length (short / medium / long) and language.
- **Interactive Q&A**: ask follow-ups; full conversation history is retained and passed to the model.
- **Page-aware context**: answers are built from page-tagged text so the model can cite pages like `[p.3]`.
- **Export**: download summaries and chat transcripts as Markdown.
- **Generation settings**: model / temperature / top-p / max-length controls.
- **OCR fallback**: optional `pdf2image` + `pytesseract` for scanned PDFs (via `.[ocr]` extras).
- **Resilient**: retries with backoff on transient Replicate errors; friendly errors for bad/empty PDFs.
- Light/dark theme via Streamlit config.

## Getting Started
1. Clone:
   ```bash
   git clone https://github.com/0xichikawa/PDF-summarizer-chatbot-using-LLaMa2
   cd PDF-summarizer-chatbot-using-LLaMa2
   ```
2. Install (base):
   ```bash
   pip install -r requirements.txt
   ```
   Or with extras:
   ```bash
   pip install -e .[ocr]   # scanned PDFs
   ```
3. Gemini API key: put it in `.streamlit/secrets.toml`:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   ```
   or `.env` as `GEMINI_API_KEY=...` (also accepts `GOOGLE_API_KEY`).
4. Run:
   ```bash
   streamlit run app.py
   ```
5. Optional Docker:
   ```bash
   docker build -t pdf-chat . && docker run -p 8501:8501 pdf-chat
   ```

## Optional system deps for OCR
- `poppler-utils` (provides `pdftoppm`)
- `tesseract-ocr`

## Limitations
- Answers are limited to ~16k chars of document context unless optional RAG extras are wired in.
- Replicate calls require a valid API token and network access; model availability/limits depend on Replicate.
- Do not upload documents containing PII/secrets you would not want sent to a third-party LLM API.

## Credits
- Meta AI for Llama.
- Replicate for API services.
- Streamlit and pypdf.
- Inspiration: Data Professor (https://github.com/dataprofessor)
