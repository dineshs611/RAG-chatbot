import streamlit as st
import os
import time
from datetime import datetime
import matplotlib.pyplot as plt

# Adjust page configuration as the absolute first action
st.set_page_config(
    page_title="EduRAG AI Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

import utils.db_manager as db
import utils.auth as auth
import utils.exporters as exporters
import utils.emailer as emailer
import parsers.manager as pm
import database.vector_store as vs
import rag.pipeline as rag
import rag.summarizer as sum_api
import rag.quiz_generator as quiz_api
import rag.flashcard_generator as fc_api
from config.settings import LANGUAGES, SUGGESTED_QUESTIONS

# Initialize session state variables
auth.init_session()

@st.cache_resource
def setup_database_schema():
    db.init_db()
    return True

setup_database_schema()

# Read and inject CSS
try:
    with open("static/style.css", "r") as f:
        custom_css = f.read()
except Exception:
    custom_css = ""

# Inject Theme Wrapper
theme_class = "light-mode-app" if st.session_state.theme == "light" else "dark-mode-app"
font_multiplier = "14px"
if st.session_state.font_size == "small":
    font_multiplier = "12px"
elif st.session_state.font_size == "large":
    font_multiplier = "18px"

css_injected = f"""
<style>
{custom_css}
html, body, [data-testid="stAppViewContainer"] {{
    font-size: {font_multiplier} !important;
}}
</style>
"""
st.markdown(f'<div class="{theme_class}">', unsafe_allow_html=True)
st.markdown(css_injected, unsafe_allow_html=True)

# Fetch translation pack
lang_pack = LANGUAGES.get(st.session_state.language, LANGUAGES["English"])

# Helper for sizes
def get_readable_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    else:
        return f"{round(size_bytes / (1024 * 1024), 1)} MB"

# --- PAGE: AUTHENTICATION ---
def show_auth_page():
    st.markdown('<div class="logo-container"><span class="logo-icon">🎓</span><span class="logo-text">EduRAG AI Assistant Portal</span></div>', unsafe_allow_html=True)
    
    tabs = st.tabs(["👨‍🎓 Student Portal", "🛡️ Admin Portal", "🔑 Forgot Password"])
    
    # Tab 1: Student Portal
    with tabs[0]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        student_tabs = st.tabs(["Student Sign In", "Student Sign Up"])
        
        with student_tabs[0]:
            st.subheader("👨‍🎓 Student Login")
            with st.form("student_login_form"):
                username = st.text_input("Username or Email", key="student_user")
                password = st.text_input("Password", type="password", key="student_pass")
                submitted = st.form_submit_button("Sign In as Student")
                
                if submitted:
                    success, msg = auth.login_user(username, password)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
        with student_tabs[1]:
            st.subheader("Create a Student Account")
            with st.form("student_register_form"):
                new_user = st.text_input("Username", key="s_reg_user")
                new_email = st.text_input("Email", key="s_reg_email")
                new_pass = st.text_input("Password", type="password", help="Minimum 6 characters", key="s_reg_pass")
                new_pass_confirm = st.text_input("Confirm Password", type="password", key="s_reg_confirm")
                submitted = st.form_submit_button("Register Student")
                
                if submitted:
                    success, msg = auth.register_user(new_user, new_email, new_pass, new_pass_confirm, role='student')
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Tab 2: Admin Portal
    with tabs[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        admin_tabs = st.tabs(["Admin Sign In", "Register New Admin"])
        
        with admin_tabs[0]:
            st.subheader("🛡️ Admin Login")
            with st.form("admin_login_form"):
                username = st.text_input("Admin Username or Email", key="admin_user")
                password = st.text_input("Admin Password", type="password", key="admin_pass")
                submitted = st.form_submit_button("Sign In as Administrator")
                
                if submitted:
                    success, msg = auth.login_user(username, password, required_role='admin')
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
        with admin_tabs[1]:
            st.subheader("Register Administrator Account")
            st.caption("Requires system Admin Secret Passcode.")
            with st.form("admin_register_form"):
                new_user = st.text_input("Admin Username", key="a_reg_user")
                new_email = st.text_input("Admin Email", key="a_reg_email")
                new_pass = st.text_input("Password", type="password", help="Minimum 6 characters", key="a_reg_pass")
                new_pass_confirm = st.text_input("Confirm Password", type="password", key="a_reg_confirm")
                passcode = st.text_input("Admin Passcode", type="password", help="Enter Admin Passcode", key="a_reg_passcode")
                submitted = st.form_submit_button("Register Admin Account")
                
                if submitted:
                    success, msg = auth.register_user(new_user, new_email, new_pass, new_pass_confirm, role='admin', admin_passcode=passcode)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Tab 3: Forgot Password
    with tabs[2]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Reset Password")
        with st.form("forgot_password_form"):
            rec_user = st.text_input("Enter your username")
            rec_email = st.text_input("Enter your registered email")
            submitted = st.form_submit_button("Generate Temporary Password")
            
            if submitted:
                success, msg = auth.simulate_password_recovery(rec_user, rec_email)
                if success:
                    st.info(msg)
                else:
                    st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)


# --- PAGE: DASHBOARD ---
def show_dashboard():
    st.title(f"👋 {lang_pack['welcome']}, {st.session_state.username}!")
    st.write("Welcome to your intelligent educational hub. Track your learning and query your study materials.")
    
    # Load User Metrics
    metrics = db.get_user_metrics(st.session_state.user_id)
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card">📚 Documents Uploaded<div class="metric-val">{metrics["uploaded_docs"]}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card">💬 Questions Asked<div class="metric-val">{metrics["questions_asked"]}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card">🎯 Quizzes Taken<div class="metric-val">{metrics["quizzes_taken"]}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card">🏆 Avg Quiz Score<div class="metric-val">{metrics["avg_quiz_score"]}%</div></div>', unsafe_allow_html=True)
        
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Storage Limit Status")
    storage_limit = 100 * 1024 * 1024  # 100 MB limit
    usage = metrics["storage_used_bytes"]
    percentage = min((usage / storage_limit) * 100, 100.0)
    
    col_pct, col_num = st.columns([4, 1])
    with col_pct:
        st.progress(percentage / 100.0)
    with col_num:
        st.write(f"{get_readable_size(usage)} / 100 MB ({round(percentage, 1)}%)")
    st.markdown('</div>', unsafe_allow_html=True)
    
    col_act, col_chat = st.columns([1, 1])
    with col_act:
        st.markdown('<div class="glass-card" style="height:100%;">', unsafe_allow_html=True)
        st.subheader("Quick Actions")
        
        # Navigation shortcuts
        if st.button("💬 Open AI Study Partner", use_container_width=True):
            st.session_state.current_page = "AI Study Partner"
            st.rerun()
        if st.button("📤 Upload Study Materials", use_container_width=True):
            st.session_state.current_page = "Upload Materials"
            st.rerun()
        if st.button("✍️ Attempt a Custom Quiz", use_container_width=True):
            st.session_state.current_page = "Quiz Generator"
            st.rerun()
        if st.button("🎴 Study Flashcards", use_container_width=True):
            st.session_state.current_page = "Flashcards"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_chat:
        st.markdown('<div class="glass-card" style="height:100%;">', unsafe_allow_html=True)
        st.subheader("Recent Chat Sessions")
        convs = db.get_user_conversations(st.session_state.user_id)
        if convs:
            for c in convs[:4]:
                col_cname, col_cgo = st.columns([4, 1])
                with col_cname:
                    st.write(f"💬 **{c['title']}** (Updated {c['updated_at'][:10]})")
                with col_cgo:
                    if st.button("Resume", key=f"dash_conv_{c['id']}"):
                        st.session_state.current_chat_id = c["id"]
                        st.session_state.current_page = "AI Study Partner"
                        st.rerun()
        else:
            st.write("No conversations found. Click below to start a new chat!")
            if st.button("New Chat", key="dash_new_chat"):
                cid = db.create_conversation(st.session_state.user_id, "Dashboard Chat")
                if cid:
                    st.session_state.current_chat_id = cid
                    st.session_state.current_page = "AI Study Partner"
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE: UPLOAD MATERIALS ---
def show_upload_materials():
    st.title("📤 Study Materials Manager")
    st.write("Upload study guides, slides, sheets, and books. Supported file formats: PDF, DOCX, CSV, Excel, TXT.")
    
    col_up, col_list = st.columns([1, 1])
    
    with col_up:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a file", 
            type=["pdf", "docx", "txt", "csv", "xlsx", "xls"],
            help="Files will be parsed, split, embedded, and indexed locally."
        )
        
        if uploaded_file is not None:
            filename = uploaded_file.name
            file_bytes = uploaded_file.read()
            file_size = len(file_bytes)
            
            # Check file size limit
            if file_size > 20 * 1024 * 1024: # 20MB file upload limit
                st.error("File exceeds 20MB limit.")
            else:
                if st.button("Process & Index Document", use_container_width=True):
                    with st.spinner("Extracting text and structure..."):
                        try:
                            # 1. Parse pages
                            pages = pm.parse_file(file_bytes, filename)
                            if not pages:
                                st.error("Failed to extract any text from the file.")
                            else:
                                # 2. Chunk text
                                chunks = pm.chunk_document(pages)
                                num_pages = len(pages)
                                num_chunks = len(chunks)
                                
                                # 3. Save file locally
                                local_dir = os.path.join("data", "uploads")
                                os.makedirs(local_dir, exist_ok=True)
                                local_path = os.path.join(local_dir, filename)
                                with open(local_path, "wb") as f:
                                    f.write(file_bytes)
                                    
                                # 4. Store metadata in SQLite database
                                doc_type = os.path.splitext(filename)[1][1:].upper()
                                doc_id = db.add_document(
                                    filename=filename,
                                    file_type=doc_type,
                                    file_size=file_size,
                                    num_chunks=num_chunks,
                                    num_pages=num_pages,
                                    uploaded_by=st.session_state.user_id,
                                    local_path=local_path
                                )
                                
                                # 5. Create Embeddings & Store in Vector DB
                                with st.spinner("Generating semantic embeddings..."):
                                    # Fetch provider from settings
                                    provider = st.session_state.get("embeddings_provider", "local")
                                    vs.add_document_chunks(
                                        doc_id=doc_id,
                                        filename=filename,
                                        file_type=doc_type,
                                        upload_date=datetime.now().isoformat(),
                                        uploaded_by=st.session_state.user_id,
                                        chunks=chunks,
                                        provider=provider
                                    )
                                    
                                st.success(f"Success! '{filename}' processed ({num_chunks} chunks, {num_pages} pages).")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Processing error: {e}")
                            db.log_event("ERROR", "uploader", f"Failed to upload {filename}: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_list:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Your Study Materials")
        docs = db.get_documents_by_user(st.session_state.user_id)
        
        if docs:
            for doc in docs:
                col_dinfo, col_ddel = st.columns([4, 1])
                with col_dinfo:
                    st.markdown(f"📄 **{doc['filename']}**")
                    st.caption(f"{doc['file_type']} | Chunks: {doc['num_chunks']} | Pages: {doc['num_pages']} | Size: {get_readable_size(doc['file_size'])}")
                with col_ddel:
                    if st.button("Delete", key=f"del_doc_{doc['id']}"):
                        # Delete vector database chunks
                        vs.delete_document_chunks(doc['id'])
                        # Delete metadata and local file
                        local_path = db.delete_document(doc['id'], st.session_state.user_id)
                        if local_path and os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except Exception as e:
                                print(f"File delete error: {e}")
                        st.success(f"Deleted '{doc['filename']}'.")
                        time.sleep(1)
                        st.rerun()
                st.divider()
        else:
            st.write("You haven't uploaded any documents yet.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE: AI STUDY PARTNER ---
def show_chat_page():
    st.title("🎓 AI Study Partner")
    
    # Initialize chat selector
    conversations = db.get_user_conversations(st.session_state.user_id)
    
    col_sidebar, col_chat = st.columns([1, 3])
    
    with col_sidebar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Chats")
        
        # New Chat button
        if st.button("+ New Study Session", use_container_width=True):
            chat_id = db.create_conversation(st.session_state.user_id, f"Study Session {len(conversations)+1}")
            if chat_id:
                st.session_state.current_chat_id = chat_id
                st.rerun()
                
        # Dropdown selection or listing
        if conversations:
            selected_idx = 0
            if st.session_state.current_chat_id:
                for idx, c in enumerate(conversations):
                    if c["id"] == st.session_state.current_chat_id:
                        selected_idx = idx
                        break
            
            c_titles = [c["title"] for c in conversations]
            sel_title = st.selectbox("Select Session", c_titles, index=selected_idx)
            
            # Map selected title to active conversation
            active_conv = conversations[c_titles.index(sel_title)]
            st.session_state.current_chat_id = active_conv["id"]
            
            # Actions on current chat
            st.write("---")
            new_title = st.text_input("Rename Session", active_conv["title"])
            if new_title != active_conv["title"] and st.button("Update Title"):
                db.rename_conversation(active_conv["id"], new_title)
                st.rerun()
                
            # Exporters download actions
            st.write("---")
            st.write("Export Dialogue")
            messages = db.get_conversation_messages(active_conv["id"])
            
            if messages:
                txt_bytes = exporters.export_to_txt(active_conv["title"], messages)
                docx_bytes = exporters.export_to_docx(active_conv["title"], messages)
                pdf_bytes = exporters.export_to_pdf(active_conv["title"], messages)
                
                st.download_button("📄 Plain Text (.txt)", txt_bytes, file_name=f"{active_conv['title']}.txt")
                st.download_button("📝 Word Doc (.docx)", docx_bytes, file_name=f"{active_conv['title']}.docx")
                st.download_button("📕 PDF Document (.pdf)", pdf_bytes, file_name=f"{active_conv['title']}.pdf")
                
            if st.button("🗑️ Delete Session", use_container_width=True):
                db.delete_conversation(active_conv["id"])
                st.session_state.current_chat_id = None
                st.rerun()
        else:
            st.write("No active study sessions. Click above to start a new chat!")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_chat:
        if st.session_state.current_chat_id:
            active_conv = None
            for c in conversations:
                if c["id"] == st.session_state.current_chat_id:
                    active_conv = c
                    break
                    
            if active_conv:
                st.markdown(f'<h3>Active Session: {active_conv["title"]}</h3>', unsafe_allow_html=True)
                
                # Filter chat by specific document if selected
                docs = db.get_documents_by_user(st.session_state.user_id)
                doc_options = ["All Uploaded Documents"] + [d["filename"] for d in docs]
                sel_doc_opt = st.selectbox("Focus study scope", doc_options)
                
                # Resolve selected document filter IDs
                doc_filter_ids = None
                if sel_doc_opt != "All Uploaded Documents":
                    focused_doc = next(d for d in docs if d["filename"] == sel_doc_opt)
                    doc_filter_ids = [focused_doc["id"]]
                    
                # Fetch chat logs
                chat_messages = db.get_conversation_messages(st.session_state.current_chat_id)
                
                # Show Chat History
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                for msg in chat_messages:
                    if msg["sender"] == "user":
                        st.markdown(f'<div class="chat-bubble chat-user">👤 <b>You:</b><br/>{msg["text"]}</div>', unsafe_allow_html=True)
                    else:
                        # Render markdown content
                        st.markdown(f'<div class="chat-bubble chat-assistant">🤖 <b>Assistant:</b><br/>{msg["text"]}</div>', unsafe_allow_html=True)
                        
                        # Render Citations (expandable block)
                        if msg.get("citations"):
                            with st.expander("📚 View source references"):
                                for cit in msg["citations"]:
                                    st.markdown(f"**Document:** {cit['document']} | **Page:** {cit.get('page', 'N/A')} | **Match Confidence:** {int(cit.get('score', 0) * 100)}%")
                                    st.caption(f"\"{cit.get('text')}\"")
                                    st.divider()
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Suggestion Chips
                st.write("Suggested questions:")
                col_s1, col_s2, col_s3 = st.columns(3)
                sugs = SUGGESTED_QUESTIONS[:3]
                
                # Form to input message
                # Note: Session states are used to submit question clicks
                question_input = st.chat_input("Ask your study materials a question...")
                
                selected_suggestion = None
                with col_s1:
                    if st.button(sugs[0], key="sug_btn_1"):
                        selected_suggestion = sugs[0]
                with col_s2:
                    if st.button(sugs[1], key="sug_btn_2"):
                        selected_suggestion = sugs[1]
                with col_s3:
                    if st.button(sugs[2], key="sug_btn_3"):
                        selected_suggestion = sugs[2]
                        
                query = question_input or selected_suggestion
                
                if query:
                    # 1. Store User Question in Database
                    db.add_message(st.session_state.current_chat_id, "user", query)
                    
                    # 2. Fetch document filter if specified
                    doc_filter_ids = None
                    if 'focused_doc_name' in st.session_state and st.session_state.focused_doc_name != "All Uploaded Documents":
                        focused_doc = next((d for d in docs if d["filename"] == st.session_state.focused_doc_name), None)
                        if focused_doc:
                            doc_filter_ids = [focused_doc["id"]]
                            
                    # 3. Execute RAG Pipeline and Store AI Response
                    with st.spinner("Analyzing document context..."):
                        llm_provider = st.session_state.get("llm_provider", "demo")
                        answer, citations = rag.execute_rag_pipeline(
                            question=query,
                            user_id=st.session_state.user_id,
                            doc_filter_ids=doc_filter_ids,
                            provider=llm_provider
                        )
                        db.add_message(st.session_state.current_chat_id, "ai", answer, citations)
                    
                    st.rerun()
        else:
            st.info("Start a new chat session to query your study materials.")

# --- PAGE: ADVANCED SEARCH ---
def show_advanced_search():
    st.title("🔍 Advanced Semantic & Keyword Search")
    st.write("Query terms, compare findings, and inspect specific data segments with filters.")
    
    docs = db.get_documents_by_user(st.session_state.user_id)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    col_q, col_type = st.columns([3, 1])
    with col_q:
        search_query = st.text_input("Enter search query")
    with col_type:
        search_mode = st.radio("Search Mode", ["Semantic Search", "Keyword Search"])
        
    st.write("**Filters**")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        doc_options = ["All Documents"] + [d["filename"] for d in docs]
        sel_doc = st.selectbox("Filter by document", doc_options)
    with col_f2:
        type_options = ["All Formats", "PDF", "DOCX", "TXT", "CSV", "XLSX"]
        sel_format = st.selectbox("Filter by format", type_options)
        
    submitted = st.button("Search database", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if submitted and search_query:
        # Resolve filter queries
        doc_ids = None
        if sel_doc != "All Documents":
            f_doc = next(d for d in docs if d["filename"] == sel_doc)
            doc_ids = [f_doc["id"]]
            
        file_format = None if sel_format == "All Formats" else sel_format.upper()
        
        with st.spinner("Searching files..."):
            # If keyword search mode, we query the local fallback db directly looking for exact string overlaps
            if search_mode == "Keyword Search":
                records = vs._load_fallback_db()
                results = []
                for r in records:
                    meta = r["metadata"]
                    # Apply filters
                    if meta.get("uploaded_by") != st.session_state.user_id:
                        continue
                    if doc_ids and meta.get("doc_id") not in doc_ids:
                        continue
                    if file_format and meta.get("file_type") != file_format:
                        continue
                        
                    # Calculate keyword occurrences count
                    query_terms = search_query.lower().split()
                    content = r["text"].lower()
                    overlap = sum(1 for term in query_terms if term in content)
                    
                    if overlap > 0:
                        results.append({
                            "text": r["text"],
                            "metadata": meta,
                            "score": float(overlap / len(query_terms))
                        })
                results.sort(key=lambda x: x["score"], reverse=True)
                results = results[:6]
            else:
                # Semantic Similarity Search
                provider = st.session_state.get("embeddings_provider", "local")
                results = vs.search_similarity(
                    query_text=search_query,
                    user_id=st.session_state.user_id,
                    doc_filter_ids=doc_ids,
                    file_type_filter=file_format,
                    top_k=6,
                    provider=provider
                )
                
        # Display results
        st.subheader(f"Search Results ({len(results)} matches)")
        if results:
            for r in results:
                meta = r["metadata"]
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.write(f"📄 **{meta.get('filename')}** (Page {meta.get('page_number')})")
                st.caption(f"Similarity Confidence Match: {int(r['score'] * 100)}%")
                st.markdown(f"```text\n{r['text'][:500]}...\n```")
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No matching documents found.")

# --- PAGE: SUMMARIZER ---
def show_summarizer():
    st.title("📝 Study Materials Summarizer")
    st.write("Generate custom structured summaries of uploaded study notes and books.")
    
    docs = db.get_documents_by_user(st.session_state.user_id)
    
    if not docs:
        st.info("Please upload documents first.")
        return
        
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    doc_titles = [d["filename"] for d in docs]
    sel_doc = st.selectbox("Select document to summarize", doc_titles)
    
    active_doc = next(d for d in docs if d["filename"] == sel_doc)
    
    sum_scope = st.radio("Summary Range", ["Entire Document", "Selected Pages"])
    
    pages_to_summarize = None
    if sum_scope == "Selected Pages":
        page_nums = list(range(1, active_doc["num_pages"] + 1))
        pages_to_summarize = st.multiselect("Select page numbers", page_nums)
        
    if st.button("Generate Summary", use_container_width=True):
        with st.spinner("Extracting content and analyzing..."):
            provider = st.session_state.get("llm_provider", "demo")
            summary = sum_api.summarize_document(
                doc_id=active_doc["id"],
                page_numbers=pages_to_summarize,
                provider=provider
            )
            st.session_state.latest_summary = summary
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    if "latest_summary" in st.session_state:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader(f"Summary: {active_doc['filename']}")
        st.write(st.session_state.latest_summary)
        
        # Download summary button
        st.download_button(
            "Download Summary Text", 
            st.session_state.latest_summary, 
            file_name=f"Summary_{active_doc['filename']}.txt"
        )
        st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE: QUIZ GENERATOR ---
def show_quiz_generator():
    st.title("🎯 AI Quiz Generator")
    st.write("Test your retention by generating custom quizzes based strictly on study guides.")
    
    docs = db.get_documents_by_user(st.session_state.user_id)
    if not docs:
        st.info("Upload documents first to generate a quiz.")
        return
        
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    doc_titles = [d["filename"] for d in docs]
    sel_doc = st.selectbox("Select source document", doc_titles)
    active_doc = next(d for d in docs if d["filename"] == sel_doc)
    
    col_num, col_diff = st.columns(2)
    with col_num:
        num_q = st.slider("Number of Questions", min_value=2, max_value=12, value=5)
    with col_diff:
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        
    q_types = st.multiselect(
        "Question Types", 
        ["Multiple Choice (MCQ)", "True/False", "Fill in the Blanks", "Short Answer"],
        default=["Multiple Choice (MCQ)", "True/False"]
    )
    
    # Map selection strings to codenames
    type_mappings = {
        "Multiple Choice (MCQ)": "mcq",
        "True/False": "tf",
        "Fill in the Blanks": "fill",
        "Short Answer": "short"
    }
    selected_types = [type_mappings[t] for t in q_types]
    
    if st.button("Generate Quiz Now", use_container_width=True):
        if not selected_types:
            st.error("Please choose at least one question type.")
        else:
            with st.spinner("Drafting questions..."):
                provider = st.session_state.get("llm_provider", "demo")
                questions = quiz_api.generate_quiz(
                    doc_id=active_doc["id"],
                    num_questions=num_q,
                    difficulty=difficulty,
                    q_types=selected_types,
                    provider=provider
                )
                if questions:
                    st.session_state.active_quiz = questions
                    st.session_state.quiz_doc_name = active_doc["filename"]
                    st.session_state.quiz_difficulty = difficulty
                    # Clear previous inputs
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_submitted = False
                else:
                    st.error("Failed to generate quiz content. Try another range.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Render Quiz Form if active
    if "active_quiz" in st.session_state and st.session_state.active_quiz:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader(f"Quiz on {st.session_state.quiz_doc_name} ({st.session_state.quiz_difficulty})")
        
        quiz_data = st.session_state.active_quiz
        
        # Display questions
        for idx, q in enumerate(quiz_data):
            q_id = q.get("id", idx + 1)
            st.write(f"### Q{q_id}. {q.get('question')}")
            
            # Answer input fields
            q_type = q.get("type", "mcq")
            if q_type == "mcq":
                opts = q.get("options", [])
                st.session_state.quiz_answers[q_id] = st.radio(
                    "Choose option:", 
                    opts, 
                    key=f"q_radio_{q_id}",
                    disabled=st.session_state.get("quiz_submitted", False)
                )
            elif q_type == "tf":
                st.session_state.quiz_answers[q_id] = st.radio(
                    "True or False:", 
                    ["True", "False"], 
                    key=f"q_tf_{q_id}",
                    disabled=st.session_state.get("quiz_submitted", False)
                )
            elif q_type == "fill":
                st.session_state.quiz_answers[q_id] = st.text_input(
                    "Write answer:", 
                    key=f"q_text_{q_id}",
                    disabled=st.session_state.get("quiz_submitted", False)
                ).strip()
            elif q_type == "short":
                st.session_state.quiz_answers[q_id] = st.text_area(
                    "Write response explanation:", 
                    key=f"q_textarea_{q_id}",
                    disabled=st.session_state.get("quiz_submitted", False)
                ).strip()
                
            st.divider()
            
        if not st.session_state.get("quiz_submitted", False):
            if st.button("Submit Quiz Answers"):
                st.session_state.quiz_submitted = True
                st.rerun()
                
        # Score results
        if st.session_state.get("quiz_submitted", False):
            correct_count = 0
            total_count = len(quiz_data)
            
            st.subheader("Quiz Results Analysis")
            
            for idx, q in enumerate(quiz_data):
                q_id = q.get("id", idx + 1)
                user_ans = st.session_state.quiz_answers.get(q_id, "")
                corr_ans = q.get("answer", "")
                q_type = q.get("type", "mcq")
                
                st.write(f"**Q{q_id}: {q.get('question')}**")
                
                is_correct = False
                if q_type == "short":
                    # Short answers are subjective, marked as reviewed
                    st.info(f"Student Response: \"{user_ans}\"\n\nModel Explanation: \"{q.get('explanation')}\"")
                    is_correct = True # Counted as points for demo scoring
                else:
                    is_correct = str(user_ans).lower() == str(corr_ans).lower()
                    if is_correct:
                        st.success(f"Correct! Your answer: \"{user_ans}\"")
                    else:
                        st.error(f"Incorrect. Your answer: \"{user_ans}\" | Correct Answer: \"{corr_ans}\"")
                    st.write(f"*Explanation:* {q.get('explanation')}")
                    
                if is_correct:
                    correct_count += 1
                st.divider()
                
            score_pct = round((correct_count / total_count) * 100, 1) if total_count > 0 else 0
            st.markdown(f'<div class="metric-card" style="margin-top:20px;"><h4>Your score: {correct_count}/{total_count} ({score_pct}%)</h4></div>', unsafe_allow_html=True)
            
            # Log results in database
            db.add_quiz_result(
                user_id=st.session_state.user_id,
                doc_name=st.session_state.quiz_doc_name,
                score=correct_count,
                total=total_count,
                difficulty=st.session_state.quiz_difficulty
            )
            
            if st.button("Close Quiz"):
                st.session_state.active_quiz = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE: FLASHCARDS ---
def show_flashcards():
    st.title("🎴 Flashcards Generator")
    st.write("Generate interactive concept flashcards to test your definitions.")
    
    docs = db.get_documents_by_user(st.session_state.user_id)
    if not docs:
        st.info("Upload documents first to generate flashcards.")
        return
        
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    doc_titles = [d["filename"] for d in docs]
    sel_doc = st.selectbox("Select document", doc_titles)
    active_doc = next(d for d in docs if d["filename"] == sel_doc)
    
    num_cards = st.slider("Number of cards", min_value=2, max_value=15, value=5)
    
    if st.button("Generate Flashcards", use_container_width=True):
        with st.spinner("Extracting definitions..."):
            provider = st.session_state.get("llm_provider", "demo")
            cards = fc_api.generate_flashcards(
                doc_id=active_doc["id"],
                num_cards=num_cards,
                provider=provider
            )
            if cards:
                st.session_state.active_cards = cards
                st.session_state.card_index = 0
                st.session_state.card_flipped = False
            else:
                st.error("Failed to generate flashcards.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Display cards if available
    if "active_cards" in st.session_state and st.session_state.active_cards:
        cards = st.session_state.active_cards
        idx = st.session_state.card_index
        
        st.write(f"### Card {idx + 1} of {len(cards)}")
        
        card = cards[idx]
        
        # Render front or back based on state
        st.markdown('<div class="flashcard-container">', unsafe_allow_html=True)
        if not st.session_state.card_flipped:
            st.markdown(f'<div class="flashcard-front"><h3>{card.get("front")}</h3><br/><small>Click Flip to see explanation</small></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="flashcard-back"><h4>Definition/Explanation:</h4><p>{card.get("back")}</p></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col_flip, col_next, col_prev = st.columns(3)
        with col_flip:
            if st.button("Flip Card", use_container_width=True):
                st.session_state.card_flipped = not st.session_state.card_flipped
                st.rerun()
        with col_next:
            if st.button("Next Card ➡️", use_container_width=True):
                st.session_state.card_index = (st.session_state.card_index + 1) % len(cards)
                st.session_state.card_flipped = False
                st.rerun()
        with col_prev:
            if st.button("⬅️ Previous Card", use_container_width=True):
                st.session_state.card_index = (st.session_state.card_index - 1 + len(cards)) % len(cards)
                st.session_state.card_flipped = False
                st.rerun()
                
        if st.button("Clear Cards"):
            st.session_state.active_cards = None
            st.rerun()

# --- PAGE: SETTINGS ---
def show_settings():
    st.title("⚙️ Personalization & Model Settings")
    st.write("Tune themes, adjust display parameters, and set active AI parameters.")
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Visual Preferences")
    
    # 1. Light/Dark Mode
    theme_opt = st.selectbox("App Theme Mode", ["Dark Mode", "Light Mode"], index=0 if st.session_state.theme == "dark" else 1)
    new_theme = "dark" if theme_opt == "Dark Mode" else "light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()
        
    # 2. Font Size
    size_opt = st.selectbox("Font Display Size", ["Small", "Medium", "Large"], index=["small", "medium", "large"].index(st.session_state.font_size))
    new_size = size_opt.lower()
    if new_size != st.session_state.font_size:
        st.session_state.font_size = new_size
        st.rerun()
        
    # 3. Language
    lang_opt = st.selectbox("UI Language", ["English", "Spanish", "French"], index=["English", "Spanish", "French"].index(st.session_state.language))
    if lang_opt != st.session_state.language:
        st.session_state.language = lang_opt
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # AI Engine Configuration
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("AI Model Configuration")
    
    active_provider = st.session_state.get("llm_provider", "demo")
    providers_list = ["Demo Mode (Offline Fallback)", "Ollama (Local Llama 3)", "OpenAI API", "Gemini API"]
    provider_keys = ["demo", "ollama", "openai", "gemini"]
    
    choice = st.selectbox(
        "Active LLM Model Provider", 
        providers_list,
        index=provider_keys.index(active_provider)
    )
    
    new_provider = provider_keys[providers_list.index(choice)]
    if new_provider != active_provider:
        st.session_state.llm_provider = new_provider
        # Set matching default embedding provider
        if new_provider in ["openai", "gemini"]:
            st.session_state.embeddings_provider = new_provider
        else:
            st.session_state.embeddings_provider = "local"
        st.success(f"Updated LLM provider to {choice}.")
        time.sleep(0.5)
        st.rerun()
        
    # API key setup in session state memory
    if new_provider == "openai":
        openai_key = st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
        if st.button("Save OpenAI Key & Activate"):
            os.environ["OPENAI_API_KEY"] = openai_key.strip()
            os.environ["DEFAULT_LLM_PROVIDER"] = "openai"
            os.environ["DEFAULT_EMBEDDINGS_PROVIDER"] = "openai"
            st.session_state.llm_provider = "openai"
            st.session_state.embeddings_provider = "openai"
            st.success("OpenAI API Key saved and activated as primary model provider!")
            time.sleep(0.5)
            st.rerun()
    elif new_provider == "gemini":
        gemini_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
        if st.button("Save Gemini Key & Activate"):
            os.environ["GEMINI_API_KEY"] = gemini_key.strip()
            os.environ["DEFAULT_LLM_PROVIDER"] = "gemini"
            os.environ["DEFAULT_EMBEDDINGS_PROVIDER"] = "gemini"
            st.session_state.llm_provider = "gemini"
            st.session_state.embeddings_provider = "gemini"
            st.success("Gemini API Key saved and activated as primary model provider!")
            time.sleep(0.5)
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE: ADMIN PANEL ---
def show_admin_panel():
    st.title("🛡️ Admin Systems Dashboard")
    st.write("Review registration metrics, examine storage size allocations, and view live logs.")
    
    # Role gate checks: Strictly allow only admin accounts
    if st.session_state.user_role != "admin":
        st.error("🚫 Access Denied: Administrator privileges required.")
        st.info("You are currently logged in with a Student account. Only users signed in through the Admin Portal can view system analytics and logs.")
        return
        
    metrics = db.get_admin_metrics()
    
    # Stat columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total System Users", metrics["total_users"])
    with col2:
        st.metric("Total Indexed Docs", metrics["total_docs"])
    with col3:
        st.metric("Total Storage Used", get_readable_size(metrics["total_storage_bytes"]))
    with col4:
        st.metric("Total Questions Queried", metrics["total_questions"])
        
    st.write("---")
    
    # Graphic plots of system metrics
    st.subheader("System Analytics Chart")
    try:
        users = metrics["users_list"]
        usernames = [u["username"] for u in users]
        doc_counts = [u["doc_count"] for u in users]
        msg_counts = [u["msg_count"] for u in users]
        
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.bar(usernames, doc_counts, label="Docs Uploaded", color="#3b82f6", alpha=0.8)
        ax.bar(usernames, msg_counts, bottom=doc_counts, label="Questions Asked", color="#7c3aed", alpha=0.8)
        ax.set_ylabel("Activity Count")
        ax.set_title("User Engagement Chart")
        ax.legend()
        st.pyplot(fig)
    except Exception as e:
        st.caption(f"Could not render matplotlib visual chart. Details: {e}")
        
    # Table of registered users
    st.write("---")
    st.subheader("System Accounts Registry")
    user_rows = []
    for u in metrics["users_list"]:
        user_rows.append({
            "ID": u["id"],
            "Username": u["username"],
            "Email": u["email"],
            "Role": u["role"],
            "Uploads Count": u["doc_count"],
            "Quizzes Taken": u["quiz_count"],
            "Queries Posed": u["msg_count"],
            "Created Date": u["created_at"][:10]
        })
    st.table(user_rows)
    
    # Document registry
    st.write("---")
    st.subheader("Global Document Indexes")
    all_docs = db.get_all_documents()
    doc_rows = []
    for d in all_docs:
        doc_rows.append({
            "Doc ID": d["id"],
            "Filename": d["filename"],
            "Format": d["file_type"],
            "Size": get_readable_size(d["file_size"]),
            "Chunks": d["num_chunks"],
            "Pages": d["num_pages"],
            "Uploader": d["uploader_name"],
            "Upload Date": d["upload_date"][:10]
        })
    if doc_rows:
        st.table(doc_rows)
    else:
        st.caption("No documents indexed in system database.")
        
    # Live System Logs
    st.write("---")
    st.subheader("Live System Logs")
    logs = db.get_system_logs(60)
    log_text = ""
    for l in logs:
        log_text += f"[{l['timestamp'][:19]}] {l['level']} ({l['module']}): {l['message']}\n"
    st.text_area("System Events", log_text, height=200)

# --- PAGE: ADMIN STUDENT ACTIVITY TRACKER ---
def show_student_activity_tracker():
    st.title("👥 Student Activity & Questions Log")
    st.write("Track student login timestamps, view questions asked by students, and examine complete activity histories.")
    
    if st.session_state.user_role != "admin":
        st.error("🚫 Access Denied: Administrator privileges required.")
        return

    tabs = st.tabs(["💬 All Student Questions", "📊 Student Activity Timelines & Timings"])

    # Tab 1: All Student Questions
    with tabs[0]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Questions Asked by Students")
        all_q = db.get_all_questions_with_users()
        
        if all_q:
            search_filter = st.text_input("Filter questions by student name or keyword", key="q_filter_input")
            
            filtered = all_q
            if search_filter:
                f_lower = search_filter.lower()
                filtered = [q for q in all_q if f_lower in q["username"].lower() or f_lower in q["question"].lower() or f_lower in q["email"].lower()]
                
            st.write(f"Displaying {len(filtered)} questions:")
            
            for q in filtered:
                st.markdown(f"👤 **Student:** `{q['username']}` ({q['email']}) | 🕒 **Timestamp:** `{q['timestamp'][:19]}`")
                st.markdown(f"💬 **Question:** {q['question']}")
                if q['ai_response']:
                    with st.expander("🤖 View AI Grounded Answer"):
                        st.write(q['ai_response'])
                st.caption(f"Session Title: {q['conversation_title']}")
                st.divider()
        else:
            st.info("No questions asked by students yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Tab 2: Individual Student Timelines & Timings
    with tabs[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        students = db.get_all_students()
        if not students:
            st.info("No student accounts registered yet.")
        else:
            student_dict = {f"{s['username']} ({s['email']})": s["id"] for s in students}
            selected_student_label = st.selectbox("Select Student Account", list(student_dict.keys()))
            selected_user_id = student_dict[selected_student_label]
            
            act = db.get_student_full_activity(selected_user_id)
            if act and act.get("user"):
                user_info = act["user"]
                st.subheader(f"Activity Profile: {user_info['username']}")
                st.write(f"📧 **Email:** {user_info['email']} | 📅 **Account Registered:** {user_info['created_at'][:19]}")
                
                sub_tabs = st.tabs(["💬 Questions Asked", "📄 Documents Uploaded", "🎯 Quiz History", "🔐 Timestamps & Logs"])
                
                with sub_tabs[0]:
                    if act["questions"]:
                        for q in act["questions"]:
                            st.write(f"🕒 **[{q['timestamp'][:19]}]** {q['question']}")
                            if q['ai_response']:
                                st.caption(f"AI Answer: {q['ai_response'][:150]}...")
                            st.divider()
                    else:
                        st.caption("No questions asked by this student.")
                        
                with sub_tabs[1]:
                    if act["documents"]:
                        for d in act["documents"]:
                            st.write(f"📄 **{d['filename']}** ({d['file_type']}) - {get_readable_size(d['file_size'])}")
                            st.caption(f"Uploaded: {d['upload_date'][:19]} | Chunks: {d['num_chunks']} | Pages: {d['num_pages']}")
                            st.divider()
                    else:
                        st.caption("No documents uploaded.")
                        
                with sub_tabs[2]:
                    if act["quizzes"]:
                        for q in act["quizzes"]:
                            score_pct = int(q['score']/q['total']*100) if q['total']>0 else 0
                            st.write(f"🎯 **Document:** {q['doc_name']} | **Score:** {q['score']}/{q['total']} ({score_pct}%) | Difficulty: {q['difficulty']}")
                            st.caption(f"Date: {q['quiz_date'][:19]}")
                            st.divider()
                    else:
                        st.caption("No quiz attempts recorded.")
                        
                with sub_tabs[3]:
                    if act["logs"]:
                        for l in act["logs"]:
                            st.write(f"🕒 **[{l['timestamp'][:19]}]** {l['message']}")
                    else:
                        st.caption("No event logs for this student.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE: ADMIN STUDENT PASSWORD MANAGEMENT ---
def show_admin_password_management():
    st.title("🔐 Student Password Management")
    st.write("Administrators can securely update or reset passwords for any registered student account.")
    
    if st.session_state.user_role != "admin":
        st.error("🚫 Access Denied: Administrator privileges required.")
        return

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    with st.expander("⚙️ Configure Live Email Server Credentials (SMTP)", expanded=not bool(os.getenv("SMTP_USER"))):
        st.write("To send real emails to students, configure your outgoing SMTP mail server credentials below (e.g. Gmail App Password).")
        with st.form("smtp_config_form"):
            smtp_srv = st.text_input("SMTP Host Server", value=os.getenv("SMTP_SERVER", "smtp.gmail.com"))
            smtp_pt = st.text_input("SMTP Port (587 for TLS, 465 for SSL)", value=os.getenv("SMTP_PORT", "587"))
            smtp_usr = st.text_input("Sender Email Address / Username", value=os.getenv("SMTP_USER", ""))
            smtp_pwd = st.text_input("SMTP App Password", value=os.getenv("SMTP_PASSWORD", ""), type="password", help="For Gmail, generate a 16-character App Password under Google Account Security.")
            
            col_save, col_test = st.columns(2)
            with col_save:
                save_smtp = st.form_submit_button("Save Credentials")
            with col_test:
                test_smtp = st.form_submit_button("Test Connection")
            
            if save_smtp:
                os.environ["SMTP_SERVER"] = smtp_srv.strip()
                os.environ["SMTP_PORT"] = smtp_pt.strip()
                os.environ["SMTP_USER"] = smtp_usr.strip()
                os.environ["SMTP_PASSWORD"] = smtp_pwd.strip()
                os.environ["SENDER_EMAIL"] = smtp_usr.strip()
                st.success("SMTP Email configuration updated successfully!")
                time.sleep(0.5)
                st.rerun()

            if test_smtp:
                with st.spinner("Testing connection to email server..."):
                    ok, test_msg = emailer.test_smtp_connection(
                        server_host=smtp_srv.strip(),
                        port=smtp_pt.strip(),
                        username=smtp_usr.strip(),
                        password=smtp_pwd.strip(),
                        sender_email=smtp_usr.strip()
                    )
                if ok:
                    st.success(test_msg)
                else:
                    st.error(test_msg)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    students = db.get_all_students()
    
    if not students:
        st.info("No student accounts available to manage.")
    else:
        student_dict = {f"{s['username']} ({s['email']})": s for s in students}
        sel_label = st.selectbox("Select Student Account to Reset", list(student_dict.keys()))
        selected_student = student_dict[sel_label]
        
        st.write(f"Managing account: **{selected_student['username']}** (`{selected_student['email']}`)")
        
        with st.form("admin_password_reset_form"):
            new_pass = st.text_input("New Password", type="password", help="Minimum 6 characters")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Update Student Password")
            
            if submitted:
                if not new_pass or len(new_pass) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                else:
                    new_hash = auth.hash_password(new_pass)
                    if db.admin_reset_user_password(selected_student["id"], new_hash):
                        st.success(f"Successfully updated password for student '{selected_student['username']}'.")
                        with st.spinner(f"Sending email notification to {selected_student['email']}..."):
                            email_ok, email_msg = emailer.send_password_reset_email(
                                to_email=selected_student['email'],
                                username=selected_student['username'],
                                temp_password=new_pass
                            )
                        if email_ok:
                            st.info(email_msg)
                        else:
                            st.warning(email_msg)
                    else:
                        st.error("Failed to update password.")
                        
        st.divider()
        st.subheader("Quick Temporary Password Generator")
        if st.button("Generate & Set Temporary Password"):
            temp_pass = f"Temp{selected_student['username']}1!"
            new_hash = auth.hash_password(temp_pass)
            if db.admin_reset_user_password(selected_student["id"], new_hash):
                st.success(f"Temporary password generated & updated for **{selected_student['username']}**: `{temp_pass}`")
                with st.spinner(f"Sending email notification to {selected_student['email']}..."):
                    email_ok, email_msg = emailer.send_password_reset_email(
                        to_email=selected_student['email'],
                        username=selected_student['username'],
                        temp_password=temp_pass
                    )
                if email_ok:
                    st.info(email_msg)
                else:
                    st.warning(email_msg)
            else:
                st.error("Failed to set temporary password.")
                
    st.markdown('</div>', unsafe_allow_html=True)

# --- APPLICATION HEADER & SIDEBAR NAVIGATION ---
def show_main_interface():
    # Sidebar rendering
    with st.sidebar:
        st.markdown('<div class="logo-container"><span class="logo-icon">🎓</span><span class="logo-text">EduRAG</span></div>', unsafe_allow_html=True)
        st.write(f"Logged in as: **{st.session_state.username}** (`{st.session_state.user_role}`)")
        st.write("---")
        
        # Navigation Mode Switcher for Administrators
        if st.session_state.user_role == "admin":
            if "admin_mode" not in st.session_state:
                st.session_state.admin_mode = True
                
            st.caption("Workspace View Mode:")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                if st.button("🛡️ Admin", type="primary" if st.session_state.admin_mode else "secondary", use_container_width=True):
                    st.session_state.admin_mode = True
                    st.session_state.current_page = "Admin Dashboard"
                    st.rerun()
            with col_m2:
                if st.button("🎓 Student", type="primary" if not st.session_state.admin_mode else "secondary", use_container_width=True):
                    st.session_state.admin_mode = False
                    st.session_state.current_page = "Dashboard"
                    st.rerun()
            st.divider()
        
        # Navigation Options: Dedicated lists based on active mode
        if st.session_state.user_role == "admin" and st.session_state.get("admin_mode", True):
            pages = [
                ("Admin Dashboard", "🏠"),
                ("Student Activity Tracker", "👥"),
                ("Student Password Reset", "🔐"),
                ("Settings", "⚙️")
            ]
        else:
            pages = [
                ("Dashboard", "🏠"),
                ("AI Study Partner", "💬"),
                ("Upload Materials", "📤"),
                ("Advanced Search", "🔍"),
                ("Summarizer", "📝"),
                ("Quiz Generator", "🎯"),
                ("Flashcards", "🎴"),
                ("Settings", "⚙️")
            ]
        
        for name, icon in pages:
            label = f"{icon} {lang_pack.get(name.lower().replace(' ', '_'), name)}"
            if st.button(label, key=f"nav_{name}", use_container_width=True):
                st.session_state.current_page = name
                st.rerun()
                
        st.write("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            auth.logout()
            st.rerun()
            
    # Page Router
    page = st.session_state.current_page
    
    if page in ["Dashboard", "Admin Dashboard"]:
        if st.session_state.user_role == "admin":
            show_admin_panel()
        else:
            show_dashboard()
    elif page == "Student Activity Tracker":
        show_student_activity_tracker()
    elif page == "Student Password Reset":
        show_admin_password_management()
    elif page == "AI Study Partner":
        show_chat_page()
    elif page == "Upload Materials":
        show_upload_materials()
    elif page == "Advanced Search":
        show_advanced_search()
    elif page == "Summarizer":
        show_summarizer()
    elif page == "Quiz Generator":
        show_quiz_generator()
    elif page == "Flashcards":
        show_flashcards()
    elif page == "Settings":
        show_settings()
    elif page == "Admin Panel":
        if st.session_state.user_role == "admin":
            show_admin_panel()
        else:
            st.error("🚫 Access Denied: Administrator privileges required.")
    else:
        st.error("Page Routing Error.")

# --- CORE ROUTER RUNNER ---
if st.session_state.authenticated:
    show_main_interface()
else:
    show_auth_page()

# Close main div wrapper
st.markdown('</div>', unsafe_allow_html=True)
