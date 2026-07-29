import re
import json
import random
from collections import Counter

def extract_keywords(text: str) -> set:
    """Extract clean lowercased words from text, ignoring stopwords."""
    stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'from', 'up', 'down', 'in', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'what', 'which', 'who', 'this', 'that', 'these', 'those'}
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return {w for w in words if w not in stopwords}

def score_sentence(sentence: str, question_keywords: set) -> float:
    """Calculate overlap score of a sentence with question keywords."""
    sent_words = extract_keywords(sentence)
    if not sent_words:
        return 0.0
    overlap = sent_words.intersection(question_keywords)
    # Jaccard-like index
    return len(overlap) / (len(question_keywords) + len(sent_words) - len(overlap) + 1)

def synthesize_answer(question: str, retrieved_chunks: list) -> str:
    """
    Synthesize an educational answer based on overlapping terms in the context.
    If similarity is low, return default 'not found' message.
    """
    question_keywords = extract_keywords(question)
    
    if not retrieved_chunks or not question_keywords:
        return "I couldn't find this information in the uploaded documents."
        
    all_sentences = []
    # Collect sentences alongside chunk metadata
    for chunk in retrieved_chunks:
        text = chunk["text"]
        meta = chunk["metadata"]
        # Split by periods, question marks, or exclamation marks followed by spaces
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 10:
                all_sentences.append({
                    "text": s_clean,
                    "score": score_sentence(s_clean, question_keywords),
                    "metadata": meta
                })
                
    # Sort sentences by score descending
    all_sentences.sort(key=lambda x: x["score"], reverse=True)
    
    # Filter out sentences that have zero keyword overlap
    relevant_sentences = [s for s in all_sentences if s["score"] > 0]
    
    if not relevant_sentences:
        return "I couldn't find this information in the uploaded documents."
        
    # Take top 4 unique scoring sentences
    selected_sents = []
    seen = set()
    for s in relevant_sentences:
        if s["text"].lower() not in seen:
            selected_sents.append(s)
            seen.add(s["text"].lower())
        if len(selected_sents) >= 4:
            break
            
    # Re-sort selections to roughly match original page orders if possible
    selected_sents.sort(key=lambda x: (x["metadata"].get("doc_id", 0), x["metadata"].get("page_number", 0), x["metadata"].get("chunk_index", 0)))
    
    # Assemble Markdown answer
    answer_parts = []
    answer_parts.append("### Grounded Summary (Demo Mode)\n")
    
    for s in selected_sents:
        page_info = f" (Page {s['metadata'].get('page_number')})" if s['metadata'].get('page_number') else ""
        doc_info = f"*{s['metadata'].get('filename')}*{page_info}"
        
        answer_parts.append(f"- {s['text']} [Source: {doc_info}]")
        
    answer_parts.append("\n> [!NOTE]\n> *You are viewing a synthesized answer in Demo Mode. To unlock advanced reasoning, switch LLM providers in Settings.*")
    
    return "\n".join(answer_parts)

def generate_demo_quiz(text: str, num_questions: int, difficulty: str, q_types: list) -> str:
    """Generate a mock quiz from text in JSON format."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 30]
    questions_list = []
    
    # Simple templates based on sentences
    q_id = 1
    
    # Clean sentences for questions
    usable_sentences = [s for s in sentences if not s.startswith("###") and "|" not in s]
    random.shuffle(usable_sentences)
    
    for sent in usable_sentences:
        if len(questions_list) >= num_questions:
            break
            
        # Parse nouns or key words to mask
        words = re.findall(r'\b[A-Z][a-z]+\b|\b\d{4}\b', sent)
        if not words:
            # Fallback to general words
            words = list(extract_keywords(sent))
            
        if not words:
            continue
            
        target_word = random.choice(words)
        
        # Determine question type
        q_type = random.choice(q_types) if q_types else "mcq"
        
        if q_type == "tf":
            # True/False question
            is_true = random.choice([True, False])
            if is_true:
                question_text = f"According to the text, is this statement True or False?\n\n\"{sent}\""
                answer = "True"
                explanation = "This matches the document content directly."
            else:
                # Alter target word slightly to make it false
                false_sent = sent.replace(target_word, f"Not-{target_word}")
                question_text = f"According to the text, is this statement True or False?\n\n\"{false_sent}\""
                answer = "False"
                explanation = f"The actual statement in the text is: \"{sent}\"."
                
            questions_list.append({
                "id": q_id,
                "type": "tf",
                "question": question_text,
                "options": ["True", "False"],
                "answer": answer,
                "explanation": explanation
            })
            q_id += 1
            
        elif q_type == "fill":
            # Fill in the blanks
            question_text = sent.replace(target_word, "_______", 1)
            questions_list.append({
                "id": q_id,
                "type": "fill",
                "question": f"Fill in the blank:\n\n{question_text}",
                "options": [],
                "answer": target_word,
                "explanation": f"The complete sentence reads: \"{sent}\"."
            })
            q_id += 1
            
        elif q_type == "short":
            # Short answer
            question_text = f"Based on the text, explain the context or detail surrounding: \"{target_word}\"?"
            questions_list.append({
                "id": q_id,
                "type": "short",
                "question": question_text,
                "options": [],
                "answer": sent,
                "explanation": f"The relevant sentence states: \"{sent}\"."
            })
            q_id += 1
            
        else:
            # MCQ (default)
            # Hide the target word
            question_text = sent.replace(target_word, "_______", 1)
            options = [target_word]
            
            # Generate fake options
            fake_words = ["Analysis", "Process", "System", "Function", "Method", "Theory", "Concept"]
            random.shuffle(fake_words)
            for f_w in fake_words:
                if len(options) >= 4:
                    break
                if f_w.lower() != target_word.lower():
                    options.append(f_w)
                    
            random.shuffle(options)
            
            questions_list.append({
                "id": q_id,
                "type": "mcq",
                "question": f"Identify the missing term:\n\n{question_text}",
                "options": options,
                "answer": target_word,
                "explanation": f"The full text contains: \"{sent}\"."
            })
            q_id += 1
            
    # Fallback if no questions could be extracted
    if not questions_list:
        questions_list.append({
            "id": 1,
            "type": "tf",
            "question": "The provided text contains educational study material.",
            "options": ["True", "False"],
            "answer": "True",
            "explanation": "Default question generated."
        })
        
    return json.dumps({"questions": questions_list})

def generate_demo_flashcards(text: str, num_cards: int) -> str:
    """Generate mock flashcards from text in JSON format."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 40]
    cards_list = []
    
    usable_sentences = [s for s in sentences if not s.startswith("###") and "|" not in s]
    random.shuffle(usable_sentences)
    
    for sent in usable_sentences:
        if len(cards_list) >= num_cards:
            break
            
        # Parse nouns or key words to use as the front
        words = re.findall(r'\b[A-Z][a-z]+\b', sent)
        if words:
            front = random.choice(words)
            # Create a simple front concept card
            cards_list.append({
                "front": f"Concept: {front}",
                "back": f"From context:\n\"{sent}\""
            })
        else:
            # Fallback using sentence split
            words = sent.split()
            if len(words) > 5:
                front = " ".join(words[:3]) + "..."
                cards_list.append({
                    "front": f"Explain: {front}",
                    "back": sent
                })
                
    if not cards_list:
        cards_list.append({
            "front": "Default Concept",
            "back": "This is a placeholder flashcard because the text was too short."
        })
        
    return json.dumps(cards_list)

def generate_demo_summary(text: str) -> str:
    """Generate text summary using extraction of top 5 sentences."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 30]
    
    # Calculate word frequency to score sentences
    words = extract_keywords(text)
    word_freq = Counter(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))
    
    sent_scores = []
    for s in sentences:
        s_words = re.findall(r'\b[a-zA-Z]{3,}\b', s.lower())
        score = sum(word_freq.get(w, 0) for w in s_words)
        sent_scores.append((score, s))
        
    # Sort and take top 5
    sent_scores.sort(key=lambda x: x[0], reverse=True)
    summary_sentences = [s[1] for s in sent_scores[:5]]
    
    # Build text summary
    summary_parts = []
    summary_parts.append("### Document Summary (Extractive Demo Mode)")
    summary_parts.append("\n**Executive Overview:**\n" + (" ".join(summary_sentences[:2])))
    summary_parts.append("\n**Key Learning Points:**")
    for s in summary_sentences[2:]:
        summary_parts.append(f"- {s}")
        
    return "\n".join(summary_parts)
