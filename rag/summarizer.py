import logging
from config.settings import DEFAULT_LLM_PROVIDER, SUMMARY_PROMPT_TEMPLATE
from rag.pipeline import generate_llm_response
from rag.demo_llm import generate_demo_summary
import database.vector_store as vs

logger = logging.getLogger("EduRAG.Summarizer")

def get_document_text(doc_id: int, page_numbers: list = None) -> str:
    """Retrieve full text of a document from the vector store or database cache."""
    # We query the vector store for all chunks belonging to this document.
    # Since we need all chunks, we can query our fallback database directly or extract
    # it. A very clean way is to load the fallback store, filter by doc_id, sort by chunk_index,
    # and join the texts. This is highly reliable!
    records = vs._load_fallback_db()
    doc_chunks = [r for r in records if r["metadata"].get("doc_id") == doc_id]
    
    if not doc_chunks:
        return ""
        
    # Sort chunks to maintain reading flow
    doc_chunks.sort(key=lambda x: (x["metadata"].get("page_number", 1), x["metadata"].get("chunk_index", 0)))
    
    selected_texts = []
    for c in doc_chunks:
        page_num = c["metadata"].get("page_number", 1)
        if page_numbers and page_num not in page_numbers:
            continue
        selected_texts.append(c["text"])
        
    return "\n\n".join(selected_texts)

def summarize_text(text: str, provider: str = None) -> str:
    """Summarize text using configured LLM provider."""
    if not text.strip():
        return "No text available to summarize."
        
    if provider is None:
        provider = DEFAULT_LLM_PROVIDER
        
    provider = provider.lower()
    
    if provider == "demo":
        return generate_demo_summary(text)
        
    # Chunk text if it is exceptionally long to prevent API overflow
    max_tokens = 6000  # Conservative token limit (approx 24k characters)
    if len(text) > 24000:
        logger.info("Text is long, performing map-reduce summary.")
        # Divide into smaller pieces
        parts = [text[i:i+24000] for i in range(0, len(text), 24000)]
        partial_summaries = []
        for part in parts:
            prompt = SUMMARY_PROMPT_TEMPLATE.format(text=part)
            partial_summaries.append(generate_llm_response(prompt, provider))
            
        combined_text = "\n\n".join(partial_summaries)
        final_prompt = SUMMARY_PROMPT_TEMPLATE.format(text=combined_text)
        return generate_llm_response(final_prompt, provider)
    else:
        prompt = SUMMARY_PROMPT_TEMPLATE.format(text=text)
        return generate_llm_response(prompt, provider)

def summarize_document(doc_id: int, page_numbers: list = None, provider: str = None) -> str:
    """Retrieve document contents and generate summary."""
    text = get_document_text(doc_id, page_numbers)
    if not text:
        return "Could not retrieve document text. Please make sure the file is properly indexed."
    return summarize_text(text, provider)
