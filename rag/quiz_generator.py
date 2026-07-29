import json
import re
import logging
from config.settings import DEFAULT_LLM_PROVIDER, QUIZ_PROMPT_TEMPLATE
from rag.pipeline import generate_llm_response
from rag.demo_llm import generate_demo_quiz
from rag.summarizer import get_document_text

logger = logging.getLogger("EduRAG.QuizGenerator")

def clean_json_string(raw_str: str) -> str:
    """Repair common LLM JSON output errors (e.g. markdown code fence wrapper)."""
    # Extract anything between ```json and ```
    match = re.search(r'```json\s*(.*?)\s*```', raw_str, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Extract anything between general ``` and ```
    match = re.search(r'```\s*(.*?)\s*```', raw_str, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    # Check for array brackets first
    start_bracket = raw_str.find('[')
    end_bracket = raw_str.rfind(']')
    start_brace = raw_str.find('{')
    end_brace = raw_str.rfind('}')
    
    if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
        if end_bracket != -1 and (end_brace == -1 or end_bracket > end_brace):
            return raw_str[start_bracket:end_bracket+1].strip()
            
    if start_brace != -1 and end_brace != -1:
        return raw_str[start_brace:end_brace+1].strip()
        
    return raw_str.strip()


def generate_quiz(doc_id: int, num_questions: int = 5, difficulty: str = "Medium", q_types: list = None, provider: str = None) -> list:
    """
    Generate quiz questions from a document.
    Returns:
        List of dicts representing quiz questions.
    """
    if q_types is None:
        q_types = ["mcq"]
        
    if provider is None:
        provider = DEFAULT_LLM_PROVIDER
        
    provider = provider.lower()
    
    # Get document content
    text = get_document_text(doc_id)
    if not text:
        return []
        
    # Limit text length to avoid token issues
    if len(text) > 15000:
        text = text[:15000]
        
    q_types_str = ", ".join(q_types)
    
    if provider == "demo":
        json_output = generate_demo_quiz(text, num_questions, difficulty, q_types)
    else:
        prompt = QUIZ_PROMPT_TEMPLATE.format(
            difficulty=difficulty,
            num_questions=num_questions,
            q_types=q_types_str,
            text=text
        )
        json_output = generate_llm_response(prompt, provider)
        
    cleaned_json = clean_json_string(json_output)
    
    try:
        data = json.loads(cleaned_json)
        if isinstance(data, dict) and "questions" in data:
            return data["questions"]
        elif isinstance(data, list):
            return data
        else:
            logger.warning(f"Unexpected JSON format: {data}")
            # Try to return fallback
            return json.loads(generate_demo_quiz(text, num_questions, difficulty, q_types))["questions"]
    except Exception as e:
        logger.error(f"Failed to parse quiz JSON: {e}. Raw input: {cleaned_json}")
        # Revert to Demo Quiz rather than crash
        try:
            return json.loads(generate_demo_quiz(text, num_questions, difficulty, q_types))["questions"]
        except:
            return []
