import logging
import requests
import json
from config.settings import (
    DEFAULT_LLM_PROVIDER, OLLAMA_API_BASE, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL, GEMINI_API_KEY, GEMINI_MODEL,
    RAG_PROMPT_TEMPLATE
)
from database.vector_store import search_similarity
from rag.demo_llm import synthesize_answer

logger = logging.getLogger("EduRAG.RAGPipeline")

def generate_llm_response(prompt: str, provider: str = None) -> str:
    """Generate raw text completion from the configured LLM provider."""
    if provider is None:
        provider = DEFAULT_LLM_PROVIDER
        
    provider = provider.lower()
    
    # 1. OpenAI Integration
    if provider == "openai":
        if not OPENAI_API_KEY:
            return "Error: OpenAI API Key is missing. Configure it in Settings."
        try:
            url = "https://api.openai.com/1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            data = {
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            res = requests.post(url, headers=headers, json=data, timeout=30)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            else:
                return f"OpenAI API Error: {res.status_code} - {res.text}"
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Failed to reach OpenAI: {e}"
            
    # 2. Gemini Integration
    elif provider == "gemini":
        if not GEMINI_API_KEY:
            return "Error: Gemini API Key is missing. Configure it in Settings."
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            headers = {
                "Content-Type": "application/json"
            }
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.2
                }
            }
            res = requests.post(url, headers=headers, json=data, timeout=30)
            if res.status_code == 200:
                # Parse Gemini response structure
                content = res.json()
                return content["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return f"Gemini API Error: {res.status_code} - {res.text}"
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Failed to reach Gemini: {e}"
            
    # 3. Ollama Integration (Local Llama 3)
    elif provider == "ollama":
        try:
            url = f"{OLLAMA_API_BASE}/api/generate"
            data = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            }
            res = requests.post(url, json=data, timeout=45)
            if res.status_code == 200:
                return res.json()["response"]
            else:
                return f"Ollama Error: {res.status_code} - {res.text}. Ensure Ollama is running locally."
        except Exception as e:
            logger.error(f"Ollama connection error: {e}")
            return f"Failed to connect to local Ollama server at {OLLAMA_API_BASE}. Ensure Ollama service is active. Details: {e}"
            
    # 4. Fallback/Demo Mode
    else:
        # For general completions in Demo mode, we just return a warning or process it using basic rules.
        # This is overridden in execute_rag_pipeline.
        return "Educational Assistant: Switch to OpenAI, Gemini, or Ollama for full reasoning capabilities."

def execute_rag_pipeline(question: str, user_id: int, doc_filter_ids: list = None, file_type_filter: str = None, provider: str = None) -> tuple:
    """
    Run full RAG pipeline:
    Embed question -> Search VectorDB -> Fetch Context Chunks -> Generate Response -> Parse Citations.
    Returns:
        (answer_text: str, citations: list)
        citations format: [{'document': str, 'page': int, 'score': float, 'text': str}]
    """
    if provider is None:
        provider = DEFAULT_LLM_PROVIDER
        
    provider = provider.lower()
    
    # 1. Similarity Search
    # Get top 5 matches
    matching_chunks = search_similarity(
        query_text=question,
        user_id=user_id,
        doc_filter_ids=doc_filter_ids,
        file_type_filter=file_type_filter,
        top_k=5
    )
    
    if not matching_chunks:
        return "I couldn't find any relevant study materials. Please upload documents first.", []
        
    # Extract citations
    citations = []
    seen_sources = set()
    for chunk in matching_chunks:
        meta = chunk["metadata"]
        filename = meta.get("filename", "Unknown Document")
        page = meta.get("page_number", 1)
        score = chunk.get("score", 0.0)
        
        # Build unique key to de-duplicate citations
        key = f"{filename}_p{page}"
        if key not in seen_sources:
            citations.append({
                "document": filename,
                "page": page,
                "score": score,
                "text": chunk["text"]
            })
            seen_sources.add(key)
            
    # 2. If provider is "demo", bypass API LLMs entirely and run locally-synthesized RAG
    if provider == "demo":
        answer = synthesize_answer(question, matching_chunks)
        # Check if the answer is the fallback negative response
        if "I couldn't find this information" in answer:
            return "I couldn't find this information in the uploaded documents.", []
        return answer, citations
        
    # 3. Assemble context block
    context_blocks = []
    for idx, chunk in enumerate(matching_chunks):
        meta = chunk["metadata"]
        block = f"[Source {idx+1}] File: {meta.get('filename')} | Page: {meta.get('page_number', 1)}\n{chunk['text']}\n"
        context_blocks.append(block)
        
    context_str = "\n---\n".join(context_blocks)
    
    # 4. Format Prompt
    prompt = RAG_PROMPT_TEMPLATE.format(context=context_str, question=question)
    
    # 5. Get Answer
    answer = generate_llm_response(prompt, provider)
    
    return answer, citations
