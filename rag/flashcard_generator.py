import json
import logging
from config.settings import DEFAULT_LLM_PROVIDER, FLASHCARD_PROMPT_TEMPLATE
from rag.pipeline import generate_llm_response
from rag.demo_llm import generate_demo_flashcards
from rag.summarizer import get_document_text
from rag.quiz_generator import clean_json_string

logger = logging.getLogger("EduRAG.FlashcardGenerator")

def generate_flashcards(doc_id: int, num_cards: int = 5, provider: str = None) -> list:
    """
    Generate educational flashcards from document content.
    Returns:
        List of dicts: [{'front': str, 'back': str}]
    """
    if provider is None:
        provider = DEFAULT_LLM_PROVIDER
        
    provider = provider.lower()
    
    # Get document text
    text = get_document_text(doc_id)
    if not text:
        return []
        
    # Limit text content to prevent token limits
    if len(text) > 12000:
        text = text[:12000]
        
    if provider == "demo":
        json_output = generate_demo_flashcards(text, num_cards)
    else:
        prompt = FLASHCARD_PROMPT_TEMPLATE.format(num_cards=num_cards, text=text)
        json_output = generate_llm_response(prompt, provider)
        
    cleaned_json = clean_json_string(json_output)
    
    try:
        # Standard clean JSON parse
        # If output is not enclosed in brackets, try wrapping it as list
        if not cleaned_json.startswith("[") and cleaned_json.startswith("{"):
            # Could be a single card object or dictionary wrapping list
            data = json.loads(cleaned_json)
            if isinstance(data, dict):
                if "flashcards" in data:
                    return data["flashcards"]
                elif "cards" in data:
                    return data["cards"]
                else:
                    return [data]
        
        cards = json.loads(cleaned_json)
        if isinstance(cards, list):
            return cards
        else:
            logger.warning(f"Unexpected flashcards JSON format: {cards}")
            return json.loads(generate_demo_flashcards(text, num_cards))
    except Exception as e:
        logger.error(f"Failed to parse flashcards JSON: {e}. Raw input: {cleaned_json}")
        try:
            return json.loads(generate_demo_flashcards(text, num_cards))
        except:
            return []
