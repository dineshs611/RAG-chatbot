import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App general settings
APP_NAME = "EduRAG AI Assistant"
VERSION = "1.0.0"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, os.getenv("SQLITE_DB_PATH", "database/edurag.db"))
CHROMA_PATH = os.path.join(BASE_DIR, os.getenv("CHROMA_DB_PATH", "database/chroma_db"))
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

# Ensure folders exist
for folder in [os.path.dirname(DB_PATH), CHROMA_PATH, UPLOADS_DIR, PROCESSED_DIR]:
    if folder:
        os.makedirs(folder, exist_ok=True)

# LLM Providers & Models
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "demo").lower()
DEFAULT_EMBEDDINGS_PROVIDER = os.getenv("DEFAULT_EMBEDDINGS_PROVIDER", "local").lower()

OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "admin123")

# RAG specific settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K_RETRIEVAL = 5

# Multilingual UI definitions
LANGUAGES = {
    "English": {
        "welcome": "Welcome back",
        "dashboard": "Dashboard",
        "chat": "AI Study Partner",
        "upload": "Upload Materials",
        "search": "Advanced Search",
        "summarizer": "Summarizer",
        "quiz": "Quiz Generator",
        "flashcards": "Flashcards",
        "admin": "Admin Panel",
        "settings": "Settings",
        "sign_out": "Sign Out",
        "no_context": "I couldn't find this information in the uploaded documents."
    },
    "Spanish": {
        "welcome": "Bienvenido de nuevo",
        "dashboard": "Tablero",
        "chat": "Compañero de Estudio IA",
        "upload": "Subir Materiales",
        "search": "Búsqueda Avanzada",
        "summarizer": "Resumidor",
        "quiz": "Generador de Cuestionarios",
        "flashcards": "Tarjetas de Memoria",
        "admin": "Panel de Admin",
        "settings": "Configuración",
        "sign_out": "Cerrar Sesión",
        "no_context": "No pude encontrar esta información en los documentos cargados."
    },
    "French": {
        "welcome": "Bon retour",
        "dashboard": "Tableau de Bord",
        "chat": "Partenaire d'Étude IA",
        "upload": "Charger des Documents",
        "search": "Recherche Avancée",
        "summarizer": "Synthétiseur",
        "quiz": "Générateur de Quiz",
        "flashcards": "Cartes Mémoire",
        "admin": "Panneau d'Admin",
        "settings": "Paramètres",
        "sign_out": "Déconnexion",
        "no_context": "Je n'ai pas trouvé cette information dans les documents téléchargés."
    }
}

# Suggestions for Educational Chat
SUGGESTED_QUESTIONS = [
    "What are the main concepts covered in the documents?",
    "Summarize the key formulas or dates mentioned.",
    "Can you explain the main argument of the uploaded study guide?",
    "Give me a bullet-point summary of the core thesis.",
    "What is the definition of the central terms in these notes?"
]

# Prompts
RAG_PROMPT_TEMPLATE = """You are an expert Educational Assistant helping a student learn from their study materials.
You must answer the student's question based strictly on the retrieved document context below.
If the answer cannot be found in the context, respond exactly with: "I couldn't find this information in the uploaded documents."
Do not make up facts, external references, or assumptions not supported by the context.

Context:
{context}

Question:
{question}

Provide a detailed, structured, educational response. Cite specific sources (filename, page numbers if any) when referencing points.
Answer:"""

SUMMARY_PROMPT_TEMPLATE = """You are an expert academic summarizer. Summarize the following document text.
Provide:
1. An overall executive summary (3-5 sentences).
2. A list of key learning objectives or core concepts.
3. 5-10 detailed bullet points detailing main explanations, dates, names, or equations.

Text to Summarize:
{text}

Summary:"""

QUIZ_PROMPT_TEMPLATE = """You are an academic test designer. Create a quiz based strictly on the document text provided below.
The quiz should have:
- Difficulty: {difficulty}
- Number of Questions: {num_questions}
- Question Types requested: {q_types}

Format the output strictly as a JSON object with a list of questions, where each question has:
- "id": unique integer starting from 1
- "type": "mcq" | "tf" | "fill" | "short"
- "question": string
- "options": list of strings (for mcq only, empty for others)
- "answer": string (the correct answer or answer key)
- "explanation": string explaining why this is correct based on the text.

Do not add any pre-amble or post-amble. Return ONLY valid JSON.

Document Text:
{text}

JSON Output:"""

FLASHCARD_PROMPT_TEMPLATE = """You are a study helper. Extract the most important concepts, terms, definitions, and theories from the following text and generate exactly {num_cards} flashcards.
Format the output strictly as a JSON list of objects, each containing:
- "front": The concept or question (keep it concise, e.g. "Photosynthesis")
- "back": The detailed explanation, definition, or answer.

Do not add any pre-amble or post-amble. Return ONLY valid JSON.

Text:
{text}

JSON Output:"""
