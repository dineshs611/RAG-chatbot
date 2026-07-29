# EduRAG AI Assistant 🎓

EduRAG AI Assistant is a premium, modern, responsive AI-powered Educational Retrieval-Augmented Generation (RAG) web application. Designed for students and educators, it allows users to upload course materials (PDF, Word, Excel, CSV, and Text files) and interact with an intelligent chat assistant that answers questions grounded strictly in the uploaded documents, complete with page citations, semantic matches, flashcards, and quiz generators.

## 🚀 Features

1. **Secure Access Management:** Complete user registry, encrypted authentication (using `bcrypt`), forgot-password flow, and custom student profiles.
2. **Interactive Study Partner:** Multi-session chat interface with suggested questions, citations overlays, source confidence scores, and instant context matching.
3. **Advanced Retrieval Pipeline:** Hybrid Semantic & Keyword search across all course materials.
4. **Smart Document Processor:** Automated parsing for PDFs, DOCX, CSV, Excel, and text documents, including real-time word-overlap sliding-window text splitters.
5. **AI Summarizer:** Generates executive summaries, learning outcomes, and key bullet points for entire documents or selected pages.
6. **Custom Quiz Maker:** Creates multiple-choice, true/false, fill-in-the-blanks, and short-answer quizzes dynamically with customized difficulty scales.
7. **Study Flashcards:** Extracts principal definitions and terms into double-sided interactive cards.
8. **Admin Panel:** Real-time metrics overview, user registries, storage logs, and system charts.
9. **Dual Database Layout:** Relational records mapped using SQLite; vector embedding vectors indexed using ChromaDB (with a built-in NumPy-based pure-Python vector database fallback to ensure zero setup issues).
10. **LLM Agnostic Integration:** Standard support for local Ollama (Llama 3), OpenAI GPT models, Gemini API, and a local Demo Generator Mode.

---

## 📁 Folder Structure

```text
EduRAG-Assistant/
├── config/
│   └── settings.py          # App configs, templates, prompts
├── data/
│   ├── uploads/             # Raw uploaded documents
│   ├── samples/             # Sample datasets for study
│   └── processed/           # Cached text data
├── database/
│   └── vector_store.py      # ChromaDB wrapper & Fallback NumPy DB
├── embeddings/
│   └── embedder.py          # Sentence-Transformers & API embedder
├── parsers/
│   ├── manager.py           # Router and text chunking logic
│   ├── pdf.py               # PyMuPDF extractor
│   ├── docx.py              # Word document extractor
│   ├── tabular.py           # Pandas CSV & Excel extractor
│   └── txt.py               # Raw text extractor
├── rag/
│   ├── pipeline.py          # Main query routing pipeline
│   ├── demo_llm.py          # Extractive NLP fallback generator
│   ├── summarizer.py        # Summarizer logic
│   ├── quiz_generator.py    # Quiz questions generator
│   └── flashcard_generator.py # Flashcards generator
├── static/
│   └── style.css            # Custom CSS for Glassmorphism
├── utils/
│   ├── auth.py              # User security and sessions
│   ├── db_manager.py        # SQLite controller
│   └── exporters.py         # PDF, DOCX, and TXT chat exporters
├── app.py                   # Main Streamlit app entrypoint
├── requirements.txt         # Project requirements
├── verify_app.py            # Automated tests suite
└── README.md                # Documentation guide
```

---

## 💻 Installation

### 1. Prerequisites
Ensure you have **Python 3.9 to 3.11** installed.

### 2. Clone and Setup
Open your terminal and run:
```bash
# Clone the repository (or navigate to directory)
cd EduRAG-Assistant

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a file named `.env` in the root directory (or edit the pre-created one):
```env
# Default provider settings: demo, ollama, openai, gemini
DEFAULT_LLM_PROVIDER=demo
DEFAULT_EMBEDDINGS_PROVIDER=local

# Ollama parameters
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=llama3

# OpenAI credentials
OPENAI_API_KEY=your_openai_api_key_here

# Gemini credentials
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## ⚙️ How to Run the App

1. Run the local development server:
   ```bash
   streamlit run app.py
   ```
2. Open your browser and navigate to `http://localhost:8501`.
3. The first registered account will automatically be assigned the **Admin** role.

---

## 🔬 Running Automated Tests

To run the verification test suite:
```bash
python verify_app.py
```

---

## 🛠️ API & Module Documentation

### `utils/db_manager.py`
Provides transactional SQLite utilities:
- `init_db()`: Sets up SQL tables.
- `create_user(username, email, pw_hash, role)`: Creates account.
- `add_document(filename, file_type, size, chunks, pages, user_id, path)`: Tracks files.
- `add_message(conv_id, sender, text, citations)`: Stores message.

### `database/vector_store.py`
Exposes the vector indexing interface:
- `add_document_chunks(...)`: Generates embeddings and stores in Chroma/Fallback DB.
- `search_similarity(query, user_id, doc_ids, format, top_k)`: Returns similarity-scored chunks.

### `rag/pipeline.py`
Main query orchestrator:
- `execute_rag_pipeline(question, user_id, doc_ids, provider)`: Retrieves context and generates grounded response.

---

## 🌐 Deployment Guide

### Deployment on Streamlit Community Cloud
1. Push your project code to a public GitHub repository.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and log in.
3. Click "New App", select your repository, branch, and `app.py` as the entrypoint.
4. Add your API keys (`OPENAI_API_KEY`, etc.) inside the **Secrets** section of the Streamlit settings console.
5. Click **Deploy!**
