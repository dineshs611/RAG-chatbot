import bcrypt
import re
import streamlit as st
import utils.db_manager as db

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def validate_email(email: str) -> bool:
    """Simple email regex check."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))

def register_user(username, email, password, confirm_password):
    """Handle new user registration details validation and database entry."""
    username = username.strip()
    email = email.strip()
    
    if not username or not email or not password:
        return False, "All fields are required."
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
        
    if not validate_email(email):
        return False, "Invalid email address format."
        
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
        
    if password != confirm_password:
        return False, "Passwords do not match."
        
    # Check if username or email already exists
    if db.get_user_by_username(username):
        return False, "Username is already taken."
        
    if db.get_user_by_email(email):
        return False, "Email is already registered."
        
    # Create user
    pw_hash = hash_password(password)
    # The first user registered in the system is automatically made an admin for administration purposes
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    
    role = "admin" if count == 0 else "student"
    
    user_id = db.create_user(username, email, pw_hash, role)
    if user_id:
        return True, "Registration successful! You can now log in."
    else:
        return False, "An error occurred during registration. Please try again."

def login_user(username, password):
    """Verify login credentials and set Streamlit session state."""
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
        
    user = db.get_user_by_username(username)
    if not user:
        # Fallback to check email
        user = db.get_user_by_email(username)
        
    if not user:
        return False, "Invalid username/email or password."
        
    if check_password(password, user["password_hash"]):
        # Establish session details
        st.session_state.authenticated = True
        st.session_state.user_id = user["id"]
        st.session_state.username = user["username"]
        st.session_state.user_role = user["role"]
        st.session_state.email = user["email"]
        if "current_page" not in st.session_state or st.session_state.current_page == "Auth":
            st.session_state.current_page = "Dashboard"
        
        db.log_event("INFO", "auth", f"User {user['username']} logged in successfully.")
        return True, "Login successful!"
        
    return False, "Invalid username/email or password."

def logout():
    """Clear credentials and terminate session state."""
    if "username" in st.session_state:
        db.log_event("INFO", "auth", f"User {st.session_state.username} logged out.")
        
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.email = None
    st.session_state.current_page = "Auth"
    st.session_state.current_chat_id = None

def init_session():
    """Verify session flags exist in Streamlit memory."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Auth"
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "font_size" not in st.session_state:
        st.session_state.font_size = "medium"
    if "language" not in st.session_state:
        st.session_state.language = "English"
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None

def simulate_password_recovery(username, email):
    """Simulate password recovery logic."""
    username = username.strip()
    email = email.strip()
    
    user = db.get_user_by_username(username)
    if not user or user["email"].lower() != email.lower():
        return False, "Username and registered email do not match."
    
    # Generate a simple mock temp password
    temp_pass = f"Temp{username}1!"
    pw_hash = hash_password(temp_pass)
    
    if db.update_user_password(username, pw_hash):
        return True, f"A temporary password has been generated for demo purposes: '{temp_pass}'. Please log in and change it immediately."
    else:
        return False, "Failed to update credentials. Try again later."
