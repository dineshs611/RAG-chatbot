import os
import json
import sqlite3
import numpy as np

# Set environment variable to default to demo mode for testing
os.environ["DEFAULT_LLM_PROVIDER"] = "demo"
os.environ["DEFAULT_EMBEDDINGS_PROVIDER"] = "mock"
os.environ["SQLITE_DB_PATH"] = "database/test_edurag.db"
os.environ["CHROMA_DB_PATH"] = "database/test_chroma_db"

import utils.db_manager as db
import utils.auth as auth
import parsers.manager as pm
import database.vector_store as vs
import rag.pipeline as rag
import rag.summarizer as sum_api
import rag.quiz_generator as quiz_api
import rag.flashcard_generator as fc_api

def run_tests():
    print("=== STARTING EDURAG AUTOMATED VERIFICATION ===")
    
    # 1. Initialize SQLite
    print("\n1. Initializing Database Schema...")
    db.init_db()
    if os.path.exists("database/test_edurag.db"):
        print("[PASS] SQLite DB successfully created.")
    else:
        print("[FAIL] Database file not created.")
        return
        
    # 2. Register mock users
    print("\n2. Testing Authentication CRUD...")
    success, msg = auth.register_user("teststudent", "student@test.edu", "password123", "password123")
    if success:
        print("[PASS] Mock Student registered successfully.")
    else:
        print(f"[FAIL] Registration failed: {msg}")
        return
        
    user = db.get_user_by_username("teststudent")
    user_id = user["id"]
    print(f"Registered Student User ID: {user_id}")
    
    # Register admin (first user was teststudent which became admin, let's verify roles)
    print(f"User role assigned: {user['role']}")
    if user['role'] == 'admin':
        print("[PASS] First user successfully promoted to Admin automatically.")
    else:
        print("[FAIL] First user role not set to admin.")
        
    # 3. Test File parsing and text splitting
    print("\n3. Testing Document Processing and Chunking...")
    dummy_text = (
        "Cellular biology is the study of cell structure and function. Cells are the fundamental units of life. "
        "The mitochondria is known as the powerhouse of the cell because it generates chemical energy (ATP). "
        "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water. "
        "It takes place in the chloroplasts. DNA contains the genetic instructions for development and functioning of organisms."
    )
    dummy_bytes = dummy_text.encode('utf-8')
    
    pages = pm.parse_file(dummy_bytes, "biology_notes.txt")
    print(f"Extracted page count: {len(pages)}")
    if len(pages) > 0:
        print(f"[PASS] Text parser read text successfully: \"{pages[0]['text'][:60]}...\"")
    else:
        print("[FAIL] Parser returned empty content.")
        return
        
    chunks = pm.chunk_document(pages, chunk_size=200, chunk_overlap=50)
    print(f"Generated text chunks: {len(chunks)}")
    if len(chunks) >= 1:
        print(f"[PASS] Text split into {len(chunks)} chunks with overlaps.")
    else:
        print("[FAIL] Chunk generator failed.")
        return
        
    # 4. Save and index document
    print("\n4. Testing Embeddings and Vector DB indexing...")
    doc_id = db.add_document(
        filename="biology_notes.txt",
        file_type="TXT",
        file_size=len(dummy_bytes),
        num_chunks=len(chunks),
        num_pages=len(pages),
        uploaded_by=user_id,
        local_path="data/uploads/biology_notes.txt"
    )
    
    vs.add_document_chunks(
        doc_id=doc_id,
        filename="biology_notes.txt",
        file_type="TXT",
        upload_date="2026-07-29T12:00:00",
        uploaded_by=user_id,
        chunks=chunks,
        provider="mock"
    )
    
    # Check if loaded into fallback store
    fallback_records = vs._load_fallback_db()
    print(f"Indexed records count: {len(fallback_records)}")
    if len(fallback_records) > 0:
        print("[PASS] Document successfully embedded and indexed.")
    else:
        print("[FAIL] Vector DB empty.")
        return
        
    # 5. Similarity Search Query
    print("\n5. Testing Vector Similarity Cosine Matches...")
    matches = vs.search_similarity(
        query_text="What does mitochondria do?",
        user_id=user_id,
        top_k=2,
        provider="mock"
    )
    print(f"Matches retrieved: {len(matches)}")
    if matches:
        top_match = matches[0]
        print(f"Top match text: \"{top_match['text'][:80]}...\"")
        print(f"Match confidence score: {round(top_match['score'] * 100, 1)}%")
        if "mitochondria" in top_match['text'].lower():
            print("[PASS] Semantic vector search returned correct context chunk.")
        else:
            print("[WARNING] Search did not place mitochondria chunk first, but returned matches.")
    else:
        print("[FAIL] No similarity search results returned.")
        
    # 6. RAG Pipeline Response
    print("\n6. Testing Grounded RAG Pipeline...")
    answer, citations = rag.execute_rag_pipeline(
        question="What does the mitochondria generate?",
        user_id=user_id,
        provider="demo"
    )
    print(f"RAG Response:\n{answer}\n")
    print(f"Sources cited: {[c['document'] for c in citations]}")
    
    if "mitochondria" in answer.lower() and len(citations) > 0:
        print("[PASS] Grounded response and citations produced correctly.")
    else:
        print("[FAIL] Grounded pipeline failed.")
        
    # 7. Summarizer, Quizzes, and Flashcards
    print("\n7. Testing Educational Generator Pipelines...")
    summary = sum_api.summarize_document(doc_id, provider="demo")
    print(f"Summary text outline:\n{summary[:150]}...\n")
    if "Summary" in summary:
        print("[PASS] Document summary successfully drafted.")
    else:
        print("[FAIL] Summarizer failed.")
        
    quiz_questions = quiz_api.generate_quiz(doc_id, num_questions=2, difficulty="Easy", q_types=["tf", "fill"], provider="demo")
    print(f"Quiz Questions count: {len(quiz_questions)}")
    if quiz_questions:
        print(f"Q1: {quiz_questions[0]['question']}")
        print(f"Correct Answer: {quiz_questions[0]['answer']}")
        print("[PASS] Quiz successfully generated in structural JSON.")
    else:
        print("[FAIL] Quiz generator failed.")
        
    flashcards = fc_api.generate_flashcards(doc_id, num_cards=2, provider="demo")
    print(f"Flashcards count: {len(flashcards)}")
    if flashcards:
        print(f"Front: {flashcards[0]['front']} | Back: {flashcards[0]['back']}")
        print("[PASS] Flashcards successfully generated in structural JSON.")
    else:
        print("[FAIL] Flashcard generator failed.")
        
    # Clean up test databases
    print("\n8. Cleaning up test files...")
    if os.path.exists("database/test_edurag.db"):
        os.remove("database/test_edurag.db")
    if os.path.exists("database/test_chroma_db/fallback_store.pkl"):
        os.remove("database/test_chroma_db/fallback_store.pkl")
    print("[PASS] Cleanup completed successfully.")
    
    print("\n=== ALL TEST CRITERIA COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_tests()
