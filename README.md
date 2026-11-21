# 📘 Company Policy Assistant

**AI-powered HR Policy Support** — an HR chatbot that answers leave, travel and reimbursement questions
using only your company's policy PDFs, and shows **which policy file and page** every answer came from.

> Academic mini-project · Problem Statement (Roll No. 34): *"Employees can't find HR policy details.
> Build a bot that answers leave, travel and reimbursement questions from policy documents."*
> Implementation requirement: *Load several policy PDFs into ChromaDB with the file name as metadata → RAG chat → show which policy file the answer came from.*

---

## 1. Project Overview

Employees upload one or more policy PDFs. The app splits them into chunks, converts the chunks to
embeddings, and stores them in a persistent **ChromaDB** database, with the **PDF file name and page number
saved as metadata on every chunk**. When an employee asks a question, the app retrieves the most relevant
chunks and sends them to **Google Gemini**, which answers strictly from that context. The answer is shown
together with the source file name and page number and the retrieved excerpt.

## 2. Objectives
- Let employees ask HR policy questions in natural language.
- Answer **only** from uploaded documents; refuse (and say so) when the documents do not contain the answer.
- Always show the source PDF filename and page number (no fabricated sources).
- Support multiple PDFs, duplicate protection, persistence across restarts and safe document removal.

## 3. Technology Stack
| Purpose | Technology |
|---|---|
| Language | Python 3.11+ (tested on 3.12) |
| Frontend | Streamlit |
| LLM | Google Gemini (`langchain-google-genai`, default `gemini-3.5-flash`) |
| Embeddings | Google Generative AI Embeddings (default `gemini-embedding-001`) |
| Orchestration | LangChain (`langchain-core`, `langchain-text-splitters`) |
| Vector DB | ChromaDB via `langchain-chroma` (persistent) |
| PDF loading | `PyPDFLoader` |
| Chunking | `RecursiveCharacterTextSplitter` (1000 chars, 150 overlap) |
| Config | `python-dotenv` |

Model names are configurable in `.env` because Google retires models periodically.

## 4. System Architecture

```
 UPLOAD PATH                                               QUESTION PATH
 ───────────                                               ─────────────
 PDF files ─► PyPDFLoader ─► page documents                Employee question
              (1 doc/page)        │                              │
                                  ▼                              ▼
                 add metadata: source=<file name>,        (follow-up? rewrite as standalone question)
                               page=<page no.>                    │
                                  │                              ▼
                 RecursiveCharacterTextSplitter            Gemini embedding of question
                                  │                              │
                                  ▼                              ▼
                 Gemini embeddings of chunks  ───►  ChromaDB (persistent, chroma_db/)
                                                             │ top-5 similar chunks + metadata
                                                             ▼
                                         Gemini + system prompt (answer ONLY from context)
                                                             │
                                                             ▼
                              Answer  +  Source: <file>.pdf | Page N  +  excerpt
```

## 5. Project Folder Structure
```
company-policy-assistant/
├── app.py                     # Streamlit UI (entry point)
├── config.py                  # settings + API key loading
├── requirements.txt
├── .env.example               # template (copy to .env)
├── .gitignore                 # excludes .env and chroma_db/
├── README.md
├── .streamlit/config.toml     # theme
├── modules/
│   ├── document_processor.py  # PDF -> chunks with filename/page metadata
│   ├── vector_store.py        # ChromaDB: add, list, duplicate check, remove, search
│   ├── rag_chain.py           # retrieval + prompt + Gemini + source extraction
│   ├── chatbot.py             # chat session, memory, validation, error handling
│   └── errors.py              # friendly error messages
├── data/
│   ├── make_sample_pdfs.py    # regenerates the DEMO PDFs
│   └── sample_policies/       # Leave_Policy.pdf, Travel_Policy.pdf, Reimbursement_Policy.pdf
├── tests/
│   ├── test_pipeline.py       # offline tests (no API key needed)
│   └── run_live_questions.py  # runs the required test questions against real Gemini
├── chroma_db/                 # generated vector database (git-ignored)
├── screenshots/
└── report/procedure_report.md
```

## 6. Installation
```bash
git clone <YOUR-GITHUB-LINK> company-policy-assistant
cd company-policy-assistant

python -m venv venv
# Windows:      venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate

pip install -r requirements.txt
```

## 7. API Key Configuration
1. Create a free key at <https://aistudio.google.com/apikey>.
2. Copy the template and edit it:
   ```bash
   cp .env.example .env        # Windows: copy .env.example .env
   ```
3. Put your key in `.env`:
   ```
   GOOGLE_API_KEY=your_real_key_here
   ```
`.env` is git-ignored — **never commit it**. The key is never shown in the UI or logs.

## 8. How to Run
```bash
streamlit run app.py
```
Open <http://localhost:8501>.

## 9. How to Upload and Process Policy PDFs
1. In the sidebar, click **Browse files** and select one or more PDFs (try the three files in `data/sample_policies/`).
2. Click **Process Documents**. A progress bar shows each file; a summary reports documents/chunks added,
   duplicates skipped, and any files that failed (corrupted, empty, password-protected, scanned images).
3. The **Indexed Documents** list shows every PDF in the database. Use the 🗑 icon to remove one
   (only its chunks are deleted). Documents stay indexed after you restart the app.
4. Ask questions in the chat box or click a suggested question.

## 10. Example Questions and Expected Outputs
> The outputs below are what the **demo PDFs** contain. Gemini's wording will differ slightly —
> replace these with your own real outputs/screenshots before submission.

| Question | Expected answer (from demo policies) | Expected source |
|---|---|---|
| How many paid leaves are allowed annually? | 18 paid leave days per year | Leave_Policy.pdf, page 1–2 |
| How many unused leaves can be carried forward? | Up to 10 days of Paid Leave; the rest lapses on 31 Dec | Leave_Policy.pdf, page 2 |
| What documents are required for travel reimbursement? | Travel Request Form, tickets/boarding passes, hotel invoices, cab receipts, expense report | Travel_Policy.pdf, page 3 |
| Who is eligible for medical reimbursement? | Confirmed full-time employees who completed the 6-month probation | Reimbursement_Policy.pdf, page 1 |
| What is the policy on employee stock options? | "The uploaded documents do not contain this information." (no source shown) | — |

You can verify real behaviour yourself with `python tests/run_live_questions.py`, which writes
`report/live_test_results.md`.

## 11. Testing
```bash
pytest -q                              # 32 offline tests, no API key needed
python tests/run_live_questions.py     # real Gemini test of the required questions
```
The offline tests replace Gemini with small fakes, so they verify the application's own logic
(extraction, metadata, page accuracy, ChromaDB persistence, duplicates, removal, prompt contents, source
attribution, error handling, UI flow) but **not** Gemini's answer quality.

## 12. Screenshots
Add your own after running the app:

| Screen | File |
|---|---|
| Home / welcome | `screenshots/01_home.png` |
| Documents processed | `screenshots/02_documents.png` |
| Answer with source | `screenshots/03_answer_with_source.png` |
| "Not in documents" response | `screenshots/04_not_found.png` |

## 13. Limitations
- Scanned/image-only PDFs are rejected (no OCR).
- Retrieval is semantic top-5 only; very long, multi-section answers can be incomplete.
- Page numbers are the PDF's physical page index (1 = first page), not printed page labels.
- A changed policy file must be removed and re-uploaded (same file name with different content is blocked on purpose).
- No user login or per-user access control.
- Free-tier Gemini rate limits can slow indexing of large PDFs (the app retries and shows a clear message).
- `PyPDFLoader` comes from `langchain-community`, which prints a "being sunset" notice at import; it still works.

## 14. Future Enhancements
OCR for scanned PDFs, hybrid keyword + semantic search, answer feedback buttons, role-based access,
policy version tracking, support for DOCX, and multilingual questions.

---
*All sample policies are fictional DEMO documents created for testing. They do not belong to any real company.*
