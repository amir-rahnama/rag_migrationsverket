# RAG Migrationsverket

The official Migrationsverket website contains a large amount of useful information, but finding the right answer can be difficult. This project was built to make that search experience more seamless — instead of navigating through pages, you can ask a question in any language (Swedish, English, Arabic, etc.) and get a direct answer grounded in official Migrationsverket documents, with source citations.

It is a fully local Retrieval Augmented Generation (RAG) system built on publicly available content from [migrationsverket.se](https://www.migrationsverket.se) — the Swedish Migration Agency.

## Demo

https://github.com/user-attachments/assets/cc1fcc2c-d3ed-4b3f-852e-7e2d200a3a13

## What it indexes

- **2,732** HTML pages from migrationsverket.se
- **425** PDF documents
- **5** DOCX documents
- **~82,000** vector chunks stored in Qdrant

## How it works

1. URLs are parsed from `sitemap1.xml` and enqueued as jobs in Redis (via RQ). Workers then crawl each URL (HTML pages, PDFs, DOCX files) in the background, with built-in retry on failure
2. The content is cleaned, chunked, and embedded using a multilingual model
3. Embeddings are stored in a local Qdrant vector database
4. When you ask a question, the most relevant chunks are retrieved and passed to a local LLM (qwen2.5:7b via Ollama) to generate an answer

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Vector database | [Qdrant](https://qdrant.tech) (local Docker) |
| Embedding model | [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) |
| LLM | [qwen3:8b](https://ollama.com/library/qwen3) via Ollama |
| Chat UI | [Chainlit](https://chainlit.io) |
| Task queue | [RQ](https://python-rq.org) + Redis |
| HTML parsing | BeautifulSoup + lxml |
| PDF extraction | pdfplumber |
| DOCX extraction | python-docx |

---

## Prerequisites

- [pyenv](https://github.com/pyenv/pyenv) + Python 3.11.13 (see `.python-version`)
- [Docker](https://www.docker.com/get-started) (for Qdrant + Redis)
- [Ollama](https://ollama.com) (for the LLM)

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd rag_migrationsverket

# pyenv will automatically pick up the correct version from .python-version
pyenv install 3.11.13   # skip if already installed
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work with local Docker)
docker compose up -d
```

This starts:
- **Qdrant** at `http://localhost:6333`
- **Redis** at `localhost:6379`

### 3. Pull the LLM

```bash
ollama pull qwen3:8b
```

---

## Building the Index

The pipeline crawls migrationsverket.se and indexes all content into Qdrant. This only needs to be done once (or when you want to refresh the data).

### Option A — Download pre-crawled data (fast)

A pre-built snapshot of all downloaded files (`data/` folder) is available on Google Drive:

**[Download data.zip](https://drive.google.com/file/d/1pac7fVvuS2XOiQ7EYz5kOKQy1O7iDa8I/view?usp=sharing)** (~25 MB)

Extract it into the project root:

```bash
unzip data.zip
```

Then skip straight to Step 2 (start the worker) — it will index from the local files without re-crawling the web.

### Option B — Crawl from scratch

### Step 1 — Enqueue all URLs

```bash
python scripts/enqueue.py
```

Reads `sitemap.xml` and pushes ~3,162 jobs into Redis queues (`crawl` for HTML, `download` for PDF/DOCX). Idempotent — safe to re-run, already-downloaded files are skipped.

### Step 2 — Start the worker

```bash
python scripts/worker.py
```

The worker processes jobs from Redis:
- Fetches HTML pages (with anti-blocking: random delays, rotating user agents)
- Downloads PDF and DOCX files
- Saves cleaned text to `data/html/`, `data/pdfs/`, `data/docx/`
- Chunks, embeds, and upserts into Qdrant

This takes several hours for the full dataset due to polite rate limiting. You can stop and restart the worker at any time — it resumes where it left off.


### Retry failed jobs
In case some of the jobs failed due to IP blockage or loss of internet connection, you can retry the failed jobs with the following commands:

```bash
python scripts/retry_failed.py            # retry all failed jobs
python scripts/retry_failed.py --dry-run  # preview without retrying
python scripts/retry_failed.py --queue crawl  # only crawl failures
```

### Reset and rebuild from scratch
If during the development, you thought you want to redo all steps, here is how you can wipe all data:

```bash
python scripts/reset.py           # wipe Redis + Qdrant (keep cached files)
python scripts/reset.py --cache   # also wipe downloaded files
```

---

## Running the Chat UI

Make sure Qdrant, Redis, and Ollama are running, then:

```bash
chainlit run app.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

Ask questions in any language — the system detects your language and responds accordingly.

---

## Running the CLI Query Tool

```bash
# Interactive mode
python scripts/query.py

# Single query
python scripts/query.py -q "Hur ansöker man om uppehållstillstånd?"
python scripts/query.py -q "How do I apply for a work permit?" --top-k 10
```

---

## Notes

- The embedding model (`multilingual-e5-large`) is ~560 MB and is downloaded automatically on first use from HuggingFace
- The LLM (`qwen2.5:7b`) is ~5 GB and must be pulled via Ollama before use
- All processing is local — no data leaves your machine
- The crawler uses 2–7 second random delays between requests to avoid being blocked

---

## Data Source & Citation

All content indexed by this system is sourced from the official website of **Migrationsverket** (the Swedish Migration Agency) and remains their copyright.

> Migrationsverket. (2024). *Official website content and publications*. Retrieved from https://www.migrationsverket.se

If you use this system or build on it, please cite both the data source and this project:

> Rahnama, A. (2025). *RAG Migrationsverket: A retrieval-augmented generation system for Swedish migration information*. GitHub. https://github.com/amirrahnama/rag_migrationsverket

---

## License

This project is licensed under **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial 4.0 International).

- You may use and adapt this project for non-commercial purposes with attribution
- Commercial use is not permitted
- The underlying data belongs to Migrationsverket and is subject to their terms

See [LICENSE](LICENSE) for full terms or visit https://creativecommons.org/licenses/by-nc/4.0/
