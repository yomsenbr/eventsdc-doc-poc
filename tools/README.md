
# EventsDC Document POC

A proof-of-concept app that ingests documents (PDF, DOCX, PPTX, TXT), extracts text (with OCR for scanned PDFs),
indexes the content (chunks + embeddings in ChromaDB), and enables **keyword**, **vector**, and **hybrid** search,
plus a lightweight **chat** endpoint with citations.

##  Features
- Upload & ingest: PDF, DOCX, PPTX, TXT (OCR for scanned PDFs with Tesseract + Poppler)
- Metadata capture: filename, type, upload date, doc_id, chunk_index, source path
- Chunking and embeddings stored in **ChromaDB**
- Search options: **keyword (BM25)**, **vector (semantic)**, **hybrid (blended)**
- **Chat** endpoint: short answers with **citations** (traceable to original docs)
- Ops endpoints: **/health**, **/stats**, and **/admin/reset**
- Meets POC goals: handles ~20 docs, returns under 15 seconds, secrets in `.env`

---

## Prerequisites (Windows)
- **Python 3.11+**
- **Tesseract OCR** (on PATH): `tesseract --version`
- **Poppler utils** (for better PDF parsing): `pdfinfo -v` (optional but recommended)
- Git (optional, for pushing to GitHub)

> If `tesseract` or `pdfinfo` are missing, install them and open a **new** PowerShell window so PATH refreshes.

---

## Setup
```powershell
# 1) clone or open your project folder
cd C:\Users\yomse\eventsdc-doc-poc

# 2) create & activate venv
python -m venv .venv
.venv\Scripts\activate

# 3) install deps
pip install -r requirements.txt

# 4) run the app
uvicorn app.main:app --reload
```

Open Swagger: http://127.0.0.1:8000/docs

---

##  Project Structure
```
eventsdc-doc-poc/
├─ app/
│  ├─ __init__.py
│  ├─ utils.py
│  ├─ ingestion.py
│  ├─ indexing.py
│  ├─ search.py
│  └─ main.py
├─ data/
│  ├─ uploads/        # original uploaded files
│  └─ processed/      # (optional) preprocessed outputs
├─ chroma_db/         # local vector index store
├─ docs/              # diagrams, slides, etc.
├─ requirements.txt
├─ .env               # (optional)
├─ .gitignore
└─ README.md
```

---

##  How to Use (Swagger)
1. **POST `/ingest`** → upload a file (PDF/DOCX/PPTX/TXT). Response shows `doc_id`, `chunks`, and `saved_path`.
2. **GET `/search/keyword`** → exact-term search (BM25).
3. **GET `/search/vector`** → semantic search (embeddings).
4. **GET `/search/hybrid`** → blended ranking (best relevance).
5. **GET `/chat`** → ask a question; get a short answer + citations.
6. **GET `/stats`** → shows total indexed chunks.
7. **GET `/health`** → `{ "ok": true }`.
8. **POST `/admin/reset`** → wipe the local index (re-ingest afterwards).

---

##  Architecture (High-level)
See **`docs/architecture_diagram.png`** (included).

**Flow**: Upload → Extract (incl. OCR) → Chunk → Embeddings → Store (ChromaDB + metadata) → Search/Chat → Results + Citations.

---

##  GitHub 
```powershell
git config --global user.name "Yomsen Tsegaye"
git config --global user.email "Yomsen.tsegaye@eventsdc.com"

git init
git add .
git commit -m "MVP complete: ingestion, search, chat, health/stats, docs"
git branch -M main
git remote add origin https://github.com/<your-username>/eventsdc-doc-poc.git
git push -u origin main
```
Use a **Personal Access Token** as password if prompted.

---

##  Troubleshooting
- **`AttributeError: ptp removed`** → ensure `app/search.py` uses `np.ptp(...)` (not `arr.ptp()`).
- **Scanned PDF not searchable** → confirm `tesseract --version` and re-open PowerShell.
- **Empty results** → ingest at least one doc, then try **/search/hybrid**.
- **Reset index** → call **POST `/admin/reset`** and re-ingest docs.
