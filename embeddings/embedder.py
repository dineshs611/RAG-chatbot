import hashlib
import numpy as np
import logging
from config.settings import DEFAULT_EMBEDDINGS_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY

logger = logging.getLogger("EduRAG.Embeddings")

# Global placeholder for the local sentence-transformer model to avoid reloading
_sentence_transformer_model = None

def get_fallback_embedding(text: str, dimension: int = 384) -> list:
    """
    Generate a deterministic, normalized word-hashing vector.
    Serves as a robust pure-Python fallback for document and query similarity matches.
    """
    words = text.lower().split()
    vector = np.zeros(dimension, dtype=np.float32)
    if not words:
        return vector.tolist()
        
    for w in words:
        # Use SHA-256 to hash the word
        h = hashlib.sha256(w.encode('utf-8')).digest()
        # Populate indexes in the vector based on hashed byte slices
        for i in range(min(len(h) // 2, dimension)):
            idx = int.from_bytes(h[i*2:(i+1)*2], byteorder='little') % dimension
            vector[idx] += 1.0
            
    # Normalize to unit vector
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()

def get_local_embedding(text: str) -> list:
    """Generate embedding using SentenceTransformers."""
    global _sentence_transformer_model
    try:
        from sentence_transformers import SentenceTransformer
        if _sentence_transformer_model is None:
            _sentence_transformer_model = SentenceTransformer('all-MiniLM-L6-v2')
        # Encode returns np.ndarray, we convert to list
        emb = _sentence_transformer_model.encode(text)
        return emb.tolist()
    except Exception as e:
        logger.warning(f"Failed to load sentence-transformers, using pure-Python hash fallback. Detail: {e}")
        return get_fallback_embedding(text)

def get_openai_embedding(text: str) -> list:
    """Generate embedding using OpenAI API."""
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key missing, falling back to local/mock embeddings.")
        return get_local_embedding(text)
    try:
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        data = {
            "input": text,
            "model": "text-embedding-3-small"
        }
        res = requests.post("https://api.openai.com/1/embeddings", headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            return res.json()["data"][0]["embedding"]
        else:
            logger.error(f"OpenAI embedding error: {res.text}")
            return get_local_embedding(text)
    except Exception as e:
        logger.error(f"OpenAI API call error: {e}")
        return get_local_embedding(text)

def get_gemini_embedding(text: str) -> list:
    """Generate embedding using Gemini REST API."""
    if not GEMINI_API_KEY:
        logger.warning("Gemini API key missing, falling back to local/mock embeddings.")
        return get_local_embedding(text)
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            return res.json()["embedding"]["values"]
        else:
            logger.error(f"Gemini embedding error: {res.text}")
            return get_local_embedding(text)
    except Exception as e:
        logger.error(f"Gemini embedding call error: {e}")
        return get_local_embedding(text)

def get_embedding(text: str, provider: str = None) -> list:
    """Main routing wrapper to fetch text embedding."""
    if provider is None:
        provider = DEFAULT_EMBEDDINGS_PROVIDER
        
    provider = provider.lower()
    
    if provider == "openai":
        return get_openai_embedding(text)
    elif provider == "gemini":
        return get_gemini_embedding(text)
    elif provider == "local":
        return get_local_embedding(text)
    else:
        return get_fallback_embedding(text)

def get_embeddings_batch(texts: list, provider: str = None) -> list:
    """Generate list of embeddings for bulk indexing."""
    # Simple iteration; can be optimized for batch-capable APIs
    return [get_embedding(t, provider) for t in texts]
