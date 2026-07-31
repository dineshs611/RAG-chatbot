import os
import pickle
import numpy as np
import logging
from config.settings import CHROMA_PATH
from embeddings.embedder import get_embedding, get_embeddings_batch

logger = logging.getLogger("EduRAG.VectorStore")

# Global flag to check if ChromaDB is available and working
_use_chroma = False
_chroma_client = None
_collection = None

# Fallback in-memory database file
FALLBACK_DB_FILE = os.path.join(CHROMA_PATH, "fallback_store.pkl")

# Attempt to load ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    
    # Initialize Persistent Client
    _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Get or create collection; we handle embeddings ourselves
    _collection = _chroma_client.get_or_create_collection(
        name="edurag_collection",
        metadata={"hnsw:space": "cosine"}
    )
    _use_chroma = True
    logger.info("ChromaDB vector store loaded successfully.")
except Exception as e:
    logger.warning(f"Could not initialize ChromaDB, falling back to NumPy-based file store. Detail: {e}")
    _use_chroma = False

# Helper for fallback store IO
def _load_fallback_db():
    if os.path.exists(FALLBACK_DB_FILE):
        try:
            with open(FALLBACK_DB_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading fallback vector store file: {e}")
            return []
    return []

def _save_fallback_db(data):
    try:
        with open(FALLBACK_DB_FILE, 'wb') as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        logger.error(f"Error saving fallback vector store file: {e}")
        return False

# --- PUBLIC FUNCTIONS ---

def add_document_chunks(doc_id: int, filename: str, file_type: str, upload_date: str, uploaded_by: int, chunks: list, provider: str = None):
    """
    Generate embeddings and index document chunks in ChromaDB or Fallback DB.
    Args:
        doc_id: SQLite primary key
        filename: name of file
        file_type: pdf, docx, txt, etc
        upload_date: timestamp string
        uploaded_by: user_id
        chunks: list of dicts: [{'text': text, 'page_number': page_num, 'chunk_index': idx}]
        provider: embedding provider (local, openai, gemini, etc.)
    """
    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings_batch(texts, provider)
    
    if _use_chroma:
        try:
            ids = [f"doc_{doc_id}_chunk_{c['chunk_index']}" for c in chunks]
            metadatas = [{
                "doc_id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "upload_date": upload_date,
                "uploaded_by": uploaded_by,
                "page_number": c["page_number"],
                "chunk_index": c["chunk_index"]
            } for c in chunks]
            
            _collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )
            logger.info(f"Indexed {len(chunks)} chunks in ChromaDB for file '{filename}'.")
            return True
        except Exception as e:
            logger.error(f"ChromaDB insert failed, attempting fallback store. Detail: {e}")
            
    # Fallback storage path
    db_records = _load_fallback_db()
    for c, emb in zip(chunks, embeddings):
        db_records.append({
            "id": f"doc_{doc_id}_chunk_{c['chunk_index']}",
            "text": c["text"],
            "embedding": emb,
            "metadata": {
                "doc_id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "upload_date": upload_date,
                "uploaded_by": uploaded_by,
                "page_number": c["page_number"],
                "chunk_index": c["chunk_index"]
            }
        })
    _save_fallback_db(db_records)
    logger.info(f"Indexed {len(chunks)} chunks in Fallback Store for file '{filename}'.")
    return True

def cosine_similarity(v1, v2):
    v1 = np.array(v1, dtype=np.float32)
    v2 = np.array(v2, dtype=np.float32)
    dot = np.dot(v1, v2)
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(dot / (n1 * n2))

def search_similarity(query_text: str, user_id: int, doc_filter_ids: list = None, file_type_filter: str = None, top_k: int = 5, provider: str = None) -> list:
    """
    Search vector database for chunks similar to the query.
    Returns:
        List of dicts: [{'text': str, 'metadata': dict, 'score': float}]
    """
    query_vector = get_embedding(query_text, provider)
    results = []
    
    if _use_chroma:
        try:
            # Build filters for Chroma DB
            where_clause = None
            if doc_filter_ids:
                # If explicit documents are selected, search across them
                pass
            elif user_id:
                where_clause = {"uploaded_by": user_id}
                
            chroma_res = _collection.query(
                query_embeddings=[query_vector],
                n_results=top_k * 3,
                where=where_clause
            )
            
            if chroma_res and chroma_res["documents"]:
                docs = chroma_res["documents"][0]
                metas = chroma_res["metadatas"][0]
                distances = chroma_res["distances"][0]
                
                for d, m, dist in zip(docs, metas, distances):
                    sim_score = float(1.0 - dist)
                    
                    # Apply in-memory filters
                    if doc_filter_ids and m.get("doc_id") not in doc_filter_ids:
                        continue
                    if file_type_filter and m.get("file_type") != file_type_filter:
                        continue
                        
                    results.append({
                        "text": d,
                        "metadata": m,
                        "score": sim_score
                    })
                    
                # Sort by score descending
                results.sort(key=lambda x: x["score"], reverse=True)
                return results[:top_k]
        except Exception as e:
            logger.error(f"ChromaDB search failed, reverting to fallback DB. Error: {e}")
            
    # Fallback search pipeline (pure Python + NumPy)
    db_records = _load_fallback_db()
    matched_records = []
    
    for r in db_records:
        meta = r["metadata"]
        # Filters:
        if doc_filter_ids:
            if meta.get("doc_id") not in doc_filter_ids:
                continue
        elif user_id:
            up_by = meta.get("uploaded_by")
            if up_by != user_id and up_by != 1:
                continue
                
        if file_type_filter and meta.get("file_type") != file_type_filter:
            continue
            
        sim = cosine_similarity(query_vector, r["embedding"])
        score = float((sim + 1.0) / 2.0) if sim is not None else 0.0
        
        matched_records.append({
            "text": r["text"],
            "metadata": meta,
            "score": score
        })
        
    matched_records.sort(key=lambda x: x["score"], reverse=True)
    return matched_records[:top_k]

def delete_document_chunks(doc_id: int):
    """Remove a document's vector index."""
    if _use_chroma:
        try:
            # Delete by metadata filter
            # Chroma where matching
            _collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted chunks for document ID {doc_id} from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"ChromaDB delete failed: {e}")
            
    # Fallback deletion
    db_records = _load_fallback_db()
    cleaned_records = [r for r in db_records if r["metadata"].get("doc_id") != doc_id]
    _save_fallback_db(cleaned_records)
    logger.info(f"Deleted chunks for document ID {doc_id} from Fallback Store.")
    return True

def clear_user_chunks(user_id: int):
    """Remove all vectors belonging to a user."""
    if _use_chroma:
        try:
            _collection.delete(where={"uploaded_by": user_id})
            return True
        except Exception as e:
            logger.error(f"ChromaDB clear user failed: {e}")
            
    db_records = _load_fallback_db()
    cleaned_records = [r for r in db_records if r["metadata"].get("uploaded_by") != user_id]
    _save_fallback_db(cleaned_records)
    return True
