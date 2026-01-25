import os
from dotenv import load_dotenv
load_dotenv()

import re
import uuid
import logging
from datetime import datetime
from docx import Document
from functools import wraps

# Database imports
import psycopg2
from psycopg2.extras import RealDictCursor

# Flask imports
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge

# AI / ML utils
from utils.speech_to_text import _get_whisper_model
from utils.speech_to_text import convert_to_text
from utils.ai_summarizer import generate_output

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB

@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash("The file you uploaded is too large. Max limit is 100MB.")
    return redirect(url_for('dashboard'))

AUDIO_EXTENSIONS = {
    "mp3", "wav", "m4a", "mp4", "avi", "mov", "mkv", "flac", "ogg"
}

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# ---------------- DATABASE ----------------
def get_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables!")
    conn = psycopg2.connect(database_url)
    return conn

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()

        # PostgreSQL uses SERIAL for auto-increment and TIMESTAMP instead of DATETIME
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                date_of_birth TEXT,
                profile_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                input_type TEXT NOT NULL,
                input_text TEXT,
                output_text TEXT NOT NULL,
                output_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

# Initialize DB on start
init_db()

# ---------------- HELPERS ----------------
def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

def get_user_by_username(username):
    conn = get_db()
    # Use RealDictCursor to access columns by name
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM users WHERE username = %s", (username,)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def save_history(user_id, input_type, input_text, output_text, output_type):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # PostgreSQL requires RETURNING id to get the last inserted ID
    cur.execute("""
        INSERT INTO history (user_id, input_type, input_text, output_text, output_type)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, input_type, input_text, output_text, output_type))
    
    new_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    return new_id 

def get_user_history(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT *
        FROM history
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Helper to generate a clean filename from the output text
def get_clean_filename(output_text, extension):
    first_line = output_text.split('\n')[0].replace('*', '')
    clean_name = re.sub(r'[\\/*?:"<>|]', "", first_line).strip()
    return f"{clean_name[:50]}.{extension}"

# ---------------- ROUTES ----------------
@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("land.html")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username")
        first = request.form.get("firstname")
        last = request.form.get("lastname")
        email = request.form.get("email")
        password = request.form.get("password")
        date = request.form.get("date")
        if len(password) < 8:
            flash("Password must be at least 8 characters long.")
            return redirect(url_for("register"))
        
        # Check if user exists
        if get_user_by_username(username):
            flash("Username already exists")
            return redirect(url_for("register"))
            
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO users (username, first_name, last_name, email, password_hash, date_of_birth)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                username, first, last, email,
                generate_password_hash(password),
                date
            ))
            conn.commit()
            flash("Registration successful")
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash("Username or Email already exists")
            return redirect(url_for("register"))
        finally:
            cur.close()
            conn.close()

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update({
                "user_id": user["id"],
                "username": user["username"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "date": user["date_of_birth"],
                "profile_image": user["profile_image"]
            })
            return redirect(url_for("dashboard"))
        
        flash("Invalid username or password")
    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    last_id = session.pop("last_history_id", None)
    selected = session.pop("selected", "notes") 
    result = None
    input_text = None

    if last_id:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT input_text, output_text FROM history WHERE id = %s", 
            (last_id,)
        )
        record = cur.fetchone()
        cur.close()
        conn.close()
        
        if record:
            result = record["output_text"]
            input_text = record["input_text"]
            
    return render_template(
        "index.html",
        user_id=session["user_id"],
        result=result,
        input_text=input_text,
        selected=selected
    )

# ---------------- UPLOAD & PROCESS ----------------
@app.route("/upload", methods=["POST"])
@login_required
def upload():  
    output_type = request.form.get("output_type", "notes")
    user_prompt = (request.form.get("user_prompt") or "").strip()
    file = request.files.get("audio_file")
    text = None
    input_type = None
    try:
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4().hex}_{filename}")
            file.save(path) 

            text = convert_to_text(path)
            input_type = "audio"
        elif user_prompt:
            text = user_prompt
            input_type = "prompt"
        else:
            flash("No input provided")
            return redirect(url_for("dashboard"))
            
        result = generate_output(text, output_type)

        last_id = save_history(session["user_id"], input_type, text, result, output_type)
        
        session["last_history_id"] = last_id
        session["selected"] = output_type
        
        return redirect(url_for("dashboard"))

    except Exception as e:
        logger.error(f"Error: {e}")
        flash("Processing failed")
        return redirect(url_for("dashboard"))

# ---------------- HISTORY ----------------
@app.route("/history")
@login_required
def history():
    query = request.args.get("q", "").strip()
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if query:
        cur.execute("""
            SELECT *
            FROM history
            WHERE user_id = %s
            AND (input_text ILIKE %s OR output_text ILIKE %s)
            ORDER BY created_at DESC
        """, (session["user_id"], f"%{query}%", f"%{query}%"))
        # Note: ILIKE is Postgres specific for case-insensitive search
    else:
        cur.execute("""
            SELECT *
            FROM history
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))
        
    records = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("history.html", records=records, query=query)

# ---------------DELETE HISTORY ITEM --------------------------
@app.route("/history/delete/<int:history_id>", methods=["POST"])
@login_required
def delete_history_item(history_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE id = %s AND user_id = %s",
        (history_id, session["user_id"]))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("history"))

# delete all history
@app.route("/history/delete_all", methods=["POST"])
@login_required
def delete_all_history():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE user_id = %s",
        (session["user_id"],))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("history"))

# ---------------- DOWNLOAD HISTORY ITEM AS PDF ----------------
@app.route("/history/<int:history_id>/pdf")
@login_required
def download_history_pdf(history_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM history WHERE id = %s AND user_id = %s", (history_id, session["user_id"]))
    record = cur.fetchone()
    cur.close()
    conn.close()
    
    if not record:
        return redirect(url_for("history"))
        
    fname = get_clean_filename(record["output_text"], "pdf")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Input:</b><br/>" + record["input_text"].replace("\n", "<br/>"), styles["Normal"]),
        Paragraph("<br/><b>Output:</b><br/>" + record["output_text"].replace("\n", "<br/>"), styles["Normal"])
    ]
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=fname, mimetype="application/pdf")

# ---------------- DOWNLOAD HISTORY ITEM AS DOCX -----------------
@app.route("/history/<int:history_id>/docx")
@login_required
def download_history_docx(history_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM history WHERE id = %s AND user_id = %s", (history_id, session["user_id"]))
    record = cur.fetchone()
    cur.close()
    conn.close()
    
    if not record:
        flash("Record not found.")
        return redirect(url_for("history"))
        
    fname = get_clean_filename(record["output_text"], "docx")
    doc = Document()
    doc.add_heading(fname.replace(".docx", ""), level=1)
    doc.add_paragraph(record["output_text"])
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=fname,mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ---------------- DOWNLOAD HISTORY ITEM AS TXT -----------------
@app.route("/history/<int:history_id>/txt")
@login_required
def download_history_txt(history_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM history WHERE id = %s AND user_id = %s", (history_id, session["user_id"]))
    record = cur.fetchone()
    cur.close()
    conn.close()
    
    if not record:
        flash("Record not found.")
        return redirect(url_for("history"))

    fname = get_clean_filename(record["output_text"], "txt")
    content = f"OUTPUT:\n{record['output_text']}"
    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=fname, mimetype="text/plain")

# ---------------- PROFILE ----------------
@app.route("/profile")
@login_required
def profile():
    dob = session.get("date")
    formatted_date = ""
    if dob:
        try:
            formatted_date = datetime.strptime(dob, "%Y-%m-%d").strftime("%d %B %Y")
        except ValueError:
            formatted_date = dob
    return render_template(
        "profile.html",
        username=session.get("username"),
        firstname=session.get("first_name"),
        lastname=session.get("last_name"),
        email=session.get("email"),
        date=formatted_date,
        profile_image=session.get("profile_image")
    )

# ---------------- DELETE ACCOUNT ----------------
@app.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    user_q = "SELECT profile_image FROM users WHERE id = %s"
    cur.execute(user_q, (user_id,))
    user = cur.fetchone()
    
    if user and user["profile_image"]:
        img_path = os.path.join(app.config["UPLOAD_FOLDER"], user["profile_image"])
        if os.path.exists(img_path):
            os.remove(img_path)
            
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    session.clear()
    flash("Your account has been permanently deleted.")
    return redirect(url_for("landing"))

# ---------------- CHANGE PASSWORD ----------------
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if len(new_password) < 8:
            flash("New password must be at least 8 characters long.")
            return redirect(url_for("change_password"))
        if not current_password or not new_password or not confirm_password:
            flash("All fields are required.")
            return redirect(url_for("change_password"))
        if new_password != confirm_password:
            flash("New passwords do not match.")
            return redirect(url_for("change_password"))
            
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT password_hash FROM users WHERE id = %s",
            (session["user_id"],)
        )
        user = cur.fetchone()
        
        if not user or not check_password_hash(user["password_hash"], current_password):
            cur.close()
            conn.close()
            flash("Current password is incorrect.")
            return redirect(url_for("change_password"))
            
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (generate_password_hash(new_password), session["user_id"])
        )
        conn.commit()
        cur.close()
        conn.close()
        
        flash("Password changed successfully.")
        return redirect(url_for("profile"))
    return render_template("change_password.html")

# ---------------- UPLOAD PROFILE PHOTO ----------------
@app.route("/upload-profile-photo", methods=["POST"])
@login_required
def upload_profile_photo():
    file = request.files.get("profile_image")
    if not file or not file.filename:
        flash("No image selected")
        return redirect(url_for("profile"))
    if not allowed_file(file.filename, IMAGE_EXTENSIONS):
        flash("Invalid image format")
        return redirect(url_for("profile"))
        
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(path)
    
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(
        "SELECT profile_image FROM users WHERE id = %s",
        (session["user_id"],)
    )
    user = cur.fetchone()

    if user and user["profile_image"]:
        old_path = os.path.join(app.config["UPLOAD_FOLDER"], user["profile_image"])
        if os.path.exists(old_path):
            os.remove(old_path)
            
    cur.execute(
        "UPDATE users SET profile_image = %s WHERE id = %s",
        (unique_name, session["user_id"])
    )
    conn.commit()
    cur.close()
    conn.close()
    
    session["profile_image"] = unique_name
    flash("Profile photo updated")
    return redirect(url_for("profile"))

# ---------------- DELETE PROFILE PHOTO ----------------
@app.route("/delete-profile-photo", methods=["POST"])
@login_required
def delete_profile_photo():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(
        "SELECT profile_image FROM users WHERE id = %s",
        (session["user_id"],)
    )
    user = cur.fetchone()
    
    if user and user["profile_image"]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], user["profile_image"])
        if os.path.exists(path):
            os.remove(path)
            
        cur.execute(
            "UPDATE users SET profile_image = NULL WHERE id = %s",
            (session["user_id"],)
        )
        conn.commit()
        
    cur.close()
    conn.close()
    
    session["profile_image"] = None
    flash("Profile photo deleted")
    return redirect(url_for("profile"))

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# --------------CACHE CONTROL-------------
@app.after_request
def add_header(response):
    """
    Force the browser to check the server every time 
    instead of loading from cache.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------- MAIN ----------------
if __name__ == "__main__":
    _get_whisper_model("tiny")
    app.run(debug=False)