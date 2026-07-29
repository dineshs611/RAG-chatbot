import sqlite3
import json
import logging
import os
from datetime import datetime
from config.settings import DB_PATH

logger = logging.getLogger("EduRAG.DB")

def get_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schemas if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at TEXT NOT NULL
    )
    """)
    
    # 2. Documents metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        num_chunks INTEGER NOT NULL,
        num_pages INTEGER DEFAULT 1,
        upload_date TEXT NOT NULL,
        uploaded_by INTEGER NOT NULL,
        local_path TEXT NOT NULL,
        FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    # 3. Conversations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    # 4. Messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender TEXT NOT NULL CHECK(sender IN ('user', 'ai')),
        text TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        citations TEXT, -- JSON string of source citations
        FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
    )
    """)
    
    # 5. System Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        level TEXT NOT NULL,
        module TEXT NOT NULL,
        message TEXT NOT NULL
    )
    """)
    
    # 6. Quiz Results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        doc_name TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        difficulty TEXT NOT NULL,
        quiz_date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()
    log_event("INFO", "db_manager", "Database initialized successfully.")

def log_event(level, module, message):
    """Write an event log into database and Python logging."""
    timestamp = datetime.now().isoformat()
    # Log to python terminal logger
    if level == "ERROR":
        logger.error(f"[{module}] {message}")
    elif level == "WARNING":
        logger.warning(f"[{module}] {message}")
    else:
        logger.info(f"[{module}] {message}")
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO system_logs (timestamp, level, module, message) VALUES (?, ?, ?, ?)",
            (timestamp, level, module, message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to write to system_logs: {e}")

# --- USER MANAGEMENT FUNCTIONS ---

def create_user(username, email, password_hash, role='student'):
    """Insert a new user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, role, created_at)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        log_event("INFO", "auth", f"User {username} registered successfully.")
        return user_id
    except sqlite3.IntegrityError as e:
        log_event("WARNING", "auth", f"Registration failed for {username}: username or email already exists.")
        return None
    except Exception as e:
        log_event("ERROR", "auth", f"Registration error: {e}")
        return None

def get_user_by_username(username):
    """Fetch user detail by username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    """Fetch user detail by email."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_password(username, new_password_hash):
    """Update user's password."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_password_hash, username))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            log_event("INFO", "auth", f"Password reset successful for {username}.")
        return success
    except Exception as e:
        log_event("ERROR", "auth", f"Password update error: {e}")
        return False

# --- DOCUMENT MANAGEMENT FUNCTIONS ---

def add_document(filename, file_type, file_size, num_chunks, num_pages, uploaded_by, local_path):
    """Register uploaded document in DB."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        upload_date = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO documents (filename, file_type, file_size, num_chunks, num_pages, upload_date, uploaded_by, local_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (filename, file_type, file_size, num_chunks, num_pages, upload_date, uploaded_by, local_path)
        )
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        log_event("INFO", "document", f"Document '{filename}' added to database. Chunks: {num_chunks}.")
        return doc_id
    except Exception as e:
        log_event("ERROR", "document", f"Add document error: {e}")
        return None

def get_documents_by_user(user_id):
    """Fetch all documents uploaded by a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE uploaded_by = ? ORDER BY upload_date DESC", (user_id,))
    docs = cursor.fetchall()
    conn.close()
    return docs

def get_all_documents():
    """Fetch all uploaded documents in the system."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, u.username as uploader_name 
        FROM documents d 
        JOIN users u ON d.uploaded_by = u.id 
        ORDER BY d.upload_date DESC
    """)
    docs = cursor.fetchall()
    conn.close()
    return docs

def delete_document(doc_id, user_id=None):
    """Delete document meta from database. Returns local path for physical deletion."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get path first
        if user_id:
            cursor.execute("SELECT local_path, filename FROM documents WHERE id = ? AND uploaded_by = ?", (doc_id, user_id))
        else:
            cursor.execute("SELECT local_path, filename FROM documents WHERE id = ?", (doc_id,))
            
        doc = cursor.fetchone()
        if not doc:
            conn.close()
            return None
            
        local_path = doc["local_path"]
        filename = doc["filename"]
        
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        log_event("INFO", "document", f"Document '{filename}' deleted from database.")
        return local_path
    except Exception as e:
        log_event("ERROR", "document", f"Delete document error: {e}")
        return None

# --- CHAT & CONVERSATION MANAGEMENT ---

def create_conversation(user_id, title="New Chat"):
    """Create a new chat conversation session."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title, created_at, created_at)
        )
        conn.commit()
        chat_id = cursor.lastrowid
        conn.close()
        log_event("INFO", "chat", f"Created conversation '{title}' (ID: {chat_id}) for user {user_id}.")
        return chat_id
    except Exception as e:
        log_event("ERROR", "chat", f"Create conversation error: {e}")
        return None

def get_user_conversations(user_id):
    """Fetch chat histories for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
    convs = cursor.fetchall()
    conn.close()
    return convs

def rename_conversation(chat_id, new_title):
    """Rename a conversation title."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?", (new_title, datetime.now().isoformat(), chat_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_event("ERROR", "chat", f"Rename conversation error: {e}")
        return False

def delete_conversation(chat_id):
    """Delete a conversation and all its messages."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (chat_id,))
        conn.commit()
        conn.close()
        log_event("INFO", "chat", f"Deleted conversation {chat_id}.")
        return True
    except Exception as e:
        log_event("ERROR", "chat", f"Delete conversation error: {e}")
        return False

def add_message(conversation_id, sender, text, citations=None):
    """Add a message to a conversation."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        citations_json = json.dumps(citations) if citations else None
        
        cursor.execute(
            "INSERT INTO messages (conversation_id, sender, text, timestamp, citations) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, sender, text, timestamp, citations_json)
        )
        # Update updated_at of conversation
        cursor.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_event("ERROR", "chat", f"Add message error: {e}")
        return False

def get_conversation_messages(conversation_id):
    """Retrieve messages for a specific conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,))
    messages = cursor.fetchall()
    conn.close()
    
    parsed_messages = []
    for msg in messages:
        cits = None
        if msg["citations"]:
            try:
                cits = json.loads(msg["citations"])
            except:
                cits = []
        parsed_messages.append({
            "id": msg["id"],
            "sender": msg["sender"],
            "text": msg["text"],
            "timestamp": msg["timestamp"],
            "citations": cits
        })
    return parsed_messages

# --- EDUCATION FEATURES TRACKING ---

def add_quiz_result(user_id, doc_name, score, total, difficulty):
    """Log a completed quiz's score."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        quiz_date = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO quiz_results (user_id, doc_name, score, total, difficulty, quiz_date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, doc_name, score, total, difficulty, quiz_date)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_event("ERROR", "quiz", f"Add quiz result error: {e}")
        return False

def get_user_quiz_results(user_id):
    """Fetch historical quiz scores for user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quiz_results WHERE user_id = ? ORDER BY quiz_date DESC", (user_id,))
    res = cursor.fetchall()
    conn.close()
    return res

# --- ANALYTICS AND SYSTEM REPORTING (ADMIN PANEL) ---

def get_admin_metrics():
    """Retrieve system analytics metrics for admin dashboards."""
    metrics = {}
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total Registered Users
    cursor.execute("SELECT COUNT(*) FROM users")
    metrics["total_users"] = cursor.fetchone()[0]
    
    # 2. Total Uploaded Docs
    cursor.execute("SELECT COUNT(*) FROM documents")
    metrics["total_docs"] = cursor.fetchone()[0]
    
    # 3. Total Storage Used
    cursor.execute("SELECT SUM(file_size) FROM documents")
    size = cursor.fetchone()[0]
    metrics["total_storage_bytes"] = size if size else 0
    
    # 4. Total Questions Asked (messages where sender = 'user')
    cursor.execute("SELECT COUNT(*) FROM messages WHERE sender = 'user'")
    metrics["total_questions"] = cursor.fetchone()[0]
    
    # 5. Active User List (Usernames, Document Counts, Quiz Count, Messages Count)
    cursor.execute("""
        SELECT u.id, u.username, u.email, u.role, u.created_at,
               (SELECT COUNT(*) FROM documents d WHERE d.uploaded_by = u.id) as doc_count,
               (SELECT COUNT(*) FROM quiz_results q WHERE q.user_id = u.id) as quiz_count,
               (SELECT COUNT(*) FROM conversations c JOIN messages m ON m.conversation_id = c.id WHERE c.user_id = u.id AND m.sender = 'user') as msg_count
        FROM users u
    """)
    metrics["users_list"] = cursor.fetchall()
    
    conn.close()
    return metrics

def get_user_metrics(user_id):
    """Retrieve key metrics for a specific user's dashboard."""
    metrics = {}
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total documents uploaded
    cursor.execute("SELECT COUNT(*) FROM documents WHERE uploaded_by = ?", (user_id,))
    metrics["uploaded_docs"] = cursor.fetchone()[0]
    
    # 2. Total storage usage
    cursor.execute("SELECT SUM(file_size) FROM documents WHERE uploaded_by = ?", (user_id,))
    size = cursor.fetchone()[0]
    metrics["storage_used_bytes"] = size if size else 0
    
    # 3. Total questions asked
    cursor.execute("""
        SELECT COUNT(*) 
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.user_id = ? AND m.sender = 'user'
    """, (user_id,))
    metrics["questions_asked"] = cursor.fetchone()[0]
    
    # 4. Quiz count
    cursor.execute("SELECT COUNT(*) FROM quiz_results WHERE user_id = ?", (user_id,))
    metrics["quizzes_taken"] = cursor.fetchone()[0]
    
    # 5. Quiz average score
    cursor.execute("SELECT score, total FROM quiz_results WHERE user_id = ?", (user_id,))
    quizzes = cursor.fetchall()
    if quizzes:
        pcts = [q[0]/q[1] for q in quizzes if q[1] > 0]
        metrics["avg_quiz_score"] = round(sum(pcts)/len(pcts) * 100, 1) if pcts else 0.0
    else:
        metrics["avg_quiz_score"] = 0.0
        
    conn.close()
    return metrics

def get_system_logs(limit=100):
    """Fetch the latest system log entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()
    return logs
