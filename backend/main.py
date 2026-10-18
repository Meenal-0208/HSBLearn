"""
HSBLearn FastAPI Application and Router Endpoints.
Implements Steps 3 to 11 of HSBLearn Specification.
"""
import os
import shutil
import uuid
import json
from pathlib import Path
from typing import List, Optional

from fastapi import (
    FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.database import get_db, init_db, seed_demo_data
from backend.models import (
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
    PasswordResetRequest, PasswordResetConfirmRequest,
    CourseCreateRequest, CourseUpdateRequest, CourseResponse, CourseAccessRequest,
    ChapterCreateRequest, ChapterResponse,
    FolderCreateRequest, FolderUpdateRequest, FolderResponse,
    MaterialResponse,
    AINotesRequest, AIRevisionSheetRequest, StudyAssetResponse, StudyAssetUpdateRequest,
    AIAskRequest, AIAskResponse,
    QuizGenerateRequest, QuizDetailResponse, QuizSubmitRequest, QuizAttemptResponse,
    VideoRecommendationsResponse,
    LearningActivityUpdateRequest, ProgressSummaryResponse
)
from backend.auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)
from backend.permissions import (
    require_instructor, require_student,
    verify_course_owner, verify_course_access,
    verify_folder_owner, verify_material_access
)
from backend.services.document_service import process_material_file
from backend.services.ai_service import (
    generate_notes, generate_revision_sheet, ask_tutor, generate_quiz
)
from backend.services.youtube_service import get_video_recommendations
from backend.services.progress_service import (
    update_learning_activity, get_student_progress_summary
)

# Initialize Storage directories
BASE_DIR = Path(__file__).resolve().parent.parent
if os.getenv("VERCEL"):
    UPLOAD_DIR = Path("/tmp/uploads")
else:
    UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="HSBLearn API",
    description="AI-native Learning Management & Personal Study Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    seed_demo_data()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "HSBLearn", "version": "1.0.0"}

# -------------------------------------------------------------
# 1. Authentication Endpoints
# -------------------------------------------------------------

@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: UserRegisterRequest):
    raise HTTPException(
        status_code=403,
        detail="Self-registration is disabled. Please contact your administrator for account access."
    )

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: UserLoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash, role, created_at FROM users WHERE email = ?", (req.email,))
        user = cursor.fetchone()
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        token = create_access_token({"sub": user["id"], "role": user["role"]})
        user_resp = UserResponse(
            id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=str(user["created_at"])
        )
        return TokenResponse(access_token=token, user=user_resp)

@app.post("/api/auth/forgot-password")
def forgot_password(req: PasswordResetRequest):
    """
    Generates a password reset token and sends an email notification.
    In local development, the reset link is printed to console and returned for instant access.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM users WHERE email = ?", (req.email,))
        user = cursor.fetchone()
        if not user:
            # Prevent email enumeration: return standard success message
            return {"status": "ok", "message": "If an account with that email exists, password reset instructions have been sent."}

        import secrets
        from datetime import datetime, timedelta
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        cursor.execute("""
            INSERT INTO password_resets (email, token, expires_at)
            VALUES (?, ?, ?)
        """, (req.email, reset_token, expires_at.strftime("%Y-%m-%d %H:%M:%S")))

        # Check SMTP settings from env (optional)
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        reset_link = f"http://127.0.0.1:9000/static/reset-password.html?token={reset_token}"

        if smtp_host and smtp_user:
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText(f"Hello {user['name']},\n\nYou requested a password reset for your HSBLearn account.\n\nClick the link below to set a new password:\n{reset_link}\n\nThis link expires in 1 hour.\nIf you did not request this, you can safely ignore this email.")
                msg['Subject'] = "HSBLearn Password Reset Request"
                msg['From'] = smtp_user
                msg['To'] = req.email

                with smtplib.SMTP(smtp_host, int(smtp_port or 587)) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            except Exception as e:
                print(f"[Mail Warning] Could not dispatch email via SMTP: {e}")

        # Always print to console for development verification
        print(f"\n[PASSWORD RESET EMAIL SENT]\nTo: {req.email}\nLink: {reset_link}\n")

        return {
            "status": "ok",
            "message": "Password reset instructions have been sent to your email.",
            "reset_link": reset_link  # Provided directly for local prototype testing
        }

@app.post("/api/auth/reset-password")
def reset_password(req: PasswordResetConfirmRequest):
    """
    Validates the reset token and updates the user's password.
    """
    from datetime import datetime
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, expires_at, used
            FROM password_resets
            WHERE token = ?
        """, (req.token,))
        record = cursor.fetchone()
        if not record or record["used"] == 1:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

        exp_time = datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() > exp_time:
            raise HTTPException(status_code=400, detail="Reset token has expired.")

        # Update password
        new_pwd_hash = get_password_hash(req.new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_pwd_hash, record["email"]))
        # Mark token as used
        cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (record["id"],))

        return {"status": "ok", "message": "Your password has been reset successfully. You can now log in."}

@app.get("/api/me", response_model=UserResponse)
def get_current_user_profile(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=str(user["created_at"])
    )

# -------------------------------------------------------------
# 2. Courses & Chapters (Shared Classroom)
# -------------------------------------------------------------

@app.get("/api/courses", response_model=List[CourseResponse])
def list_courses(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        if user["role"] == "instructor":
            cursor.execute("""
                SELECT c.*, u.name as instructor_name,
                (SELECT COUNT(*) FROM chapters WHERE course_id = c.id) as total_chapters,
                (SELECT COUNT(*) FROM materials WHERE course_id = c.id) as total_materials
                FROM courses c
                JOIN users u ON c.instructor_id = u.id
                WHERE c.instructor_id = ?
                ORDER BY c.created_at DESC
            """, (user["id"],))
        else:
            # All published courses are visible to students in the shared classroom
            cursor.execute("""
                SELECT c.*, u.name as instructor_name,
                (SELECT COUNT(*) FROM chapters WHERE course_id = c.id) as total_chapters,
                (SELECT COUNT(*) FROM materials WHERE course_id = c.id) as total_materials
                FROM courses c
                JOIN users u ON c.instructor_id = u.id
                WHERE c.status = 'published'
                ORDER BY c.created_at DESC
            """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@app.post("/api/courses", response_model=CourseResponse)
def create_course(req: CourseCreateRequest, user: dict = Depends(get_current_user)):
    require_instructor(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO courses (title, description, instructor_id, status)
            VALUES (?, ?, ?, 'published')
        """, (req.title, req.description, user["id"]))
        course_id = cursor.lastrowid

        cursor.execute("SELECT c.*, u.name as instructor_name FROM courses c JOIN users u ON c.instructor_id = u.id WHERE c.id = ?", (course_id,))
        course = cursor.fetchone()
        return dict(course)

@app.get("/api/courses/{course_id}", response_model=CourseResponse)
def get_course_detail(course_id: int, user: dict = Depends(get_current_user)):
    verify_course_access(user, course_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, u.name as instructor_name,
            (SELECT COUNT(*) FROM chapters WHERE course_id = c.id) as total_chapters,
            (SELECT COUNT(*) FROM materials WHERE course_id = c.id) as total_materials
            FROM courses c
            JOIN users u ON c.instructor_id = u.id
            WHERE c.id = ?
        """, (course_id,))
        course = cursor.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found.")
        return dict(course)

@app.patch("/api/courses/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, req: CourseUpdateRequest, user: dict = Depends(get_current_user)):
    verify_course_owner(user, course_id)
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if req.title is not None:
            updates.append("title = ?")
            params.append(req.title)
        if req.description is not None:
            updates.append("description = ?")
            params.append(req.description)
        if req.status is not None:
            updates.append("status = ?")
            params.append(req.status)
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(course_id)
            cursor.execute(f"UPDATE courses SET {', '.join(updates)} WHERE id = ?", params)
        
        cursor.execute("SELECT c.*, u.name as instructor_name FROM courses c JOIN users u ON c.instructor_id = u.id WHERE c.id = ?", (course_id,))
        return dict(cursor.fetchone())

@app.post("/api/courses/{course_id}/chapters", response_model=ChapterResponse)
def create_chapter(course_id: int, req: ChapterCreateRequest, user: dict = Depends(get_current_user)):
    verify_course_owner(user, course_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chapters (course_id, title, description, order_index)
            VALUES (?, ?, ?, ?)
        """, (course_id, req.title, req.description, req.order_index))
        chapter_id = cursor.lastrowid
        cursor.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
        return dict(cursor.fetchone())

@app.get("/api/courses/{course_id}/chapters", response_model=List[ChapterResponse])
def list_chapters(course_id: int, user: dict = Depends(get_current_user)):
    verify_course_access(user, course_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chapters WHERE course_id = ? ORDER BY order_index ASC", (course_id,))
        return [dict(r) for r in cursor.fetchall()]

@app.post("/api/courses/{course_id}/access")
def grant_course_access(course_id: int, req: CourseAccessRequest, user: dict = Depends(get_current_user)):
    verify_course_owner(user, course_id)
    with get_db() as conn:
        cursor = conn.cursor()
        student_id = req.student_id
        if not student_id and req.student_email:
            cursor.execute("SELECT id FROM users WHERE email = ? AND role = 'student'", (req.student_email,))
            st = cursor.fetchone()
            if not st:
                raise HTTPException(status_code=404, detail="Student email not found.")
            student_id = st["id"]

        if not student_id:
            raise HTTPException(status_code=400, detail="Must provide student_id or student_email.")

        cursor.execute("""
            INSERT INTO course_access (course_id, student_id, status)
            VALUES (?, ?, 'active')
            ON CONFLICT(course_id, student_id) DO UPDATE SET status = 'active'
        """, (course_id, student_id))
        return {"status": "ok", "message": f"Student {student_id} granted active access to course {course_id}."}

# -------------------------------------------------------------
# 3. Personal Folders (My Study Space)
# -------------------------------------------------------------

@app.get("/api/study-space/folders", response_model=List[FolderResponse])
def list_personal_folders(user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.*,
            (SELECT COUNT(*) FROM personal_folders WHERE parent_folder_id = f.id) as subfolders_count,
            (SELECT COUNT(*) FROM materials WHERE personal_folder_id = f.id) as materials_count
            FROM personal_folders f
            WHERE f.student_id = ?
            ORDER BY f.created_at ASC
        """, (user["id"],))
        return [dict(r) for r in cursor.fetchall()]

@app.post("/api/study-space/folders", response_model=FolderResponse)
def create_personal_folder(req: FolderCreateRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    if req.parent_folder_id:
        verify_folder_owner(user, req.parent_folder_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO personal_folders (student_id, parent_folder_id, name)
            VALUES (?, ?, ?)
        """, (user["id"], req.parent_folder_id, req.name))
        folder_id = cursor.lastrowid
        cursor.execute("SELECT * FROM personal_folders WHERE id = ?", (folder_id,))
        return dict(cursor.fetchone())

@app.patch("/api/study-space/folders/{folder_id}", response_model=FolderResponse)
def update_personal_folder(folder_id: int, req: FolderUpdateRequest, user: dict = Depends(get_current_user)):
    verify_folder_owner(user, folder_id)
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if req.name is not None:
            updates.append("name = ?")
            params.append(req.name)
        if req.parent_folder_id is not None:
            if req.parent_folder_id == folder_id:
                raise HTTPException(status_code=400, detail="Folder cannot be its own parent.")
            updates.append("parent_folder_id = ?")
            params.append(req.parent_folder_id)
        if updates:
            params.append(folder_id)
            cursor.execute(f"UPDATE personal_folders SET {', '.join(updates)} WHERE id = ?", params)
        cursor.execute("SELECT * FROM personal_folders WHERE id = ?", (folder_id,))
        return dict(cursor.fetchone())

@app.delete("/api/study-space/folders/{folder_id}")
def delete_personal_folder(folder_id: int, user: dict = Depends(get_current_user)):
    verify_folder_owner(user, folder_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM personal_folders WHERE id = ?", (folder_id,))
        return {"status": "ok", "message": "Folder deleted successfully."}

# -------------------------------------------------------------
# 4. Materials Upload & Management (Shared & Study Space)
# -------------------------------------------------------------

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt", ".md"}

def save_uploaded_file(file: UploadFile) -> str:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: PDF, DOCX, PPTX, TXT")
    
    unique_filename = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    storage_path = UPLOAD_DIR / unique_filename
    with open(storage_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return str(storage_path)

@app.post("/api/courses/{course_id}/materials", response_model=List[MaterialResponse])
async def upload_course_materials(
    course_id: int,
    chapter_id: Optional[int] = Form(None),
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user)
):
    verify_course_owner(user, course_id)
    uploaded_records = []

    for file in files:
        storage_path = save_uploaded_file(file)
        file_size = os.path.getsize(storage_path)
        ext = Path(file.filename).suffix.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO materials (
                    uploader_id, course_id, chapter_id, personal_folder_id,
                    file_name, file_type, storage_path, file_size, visibility, extraction_status
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 'course', 'pending')
            """, (user["id"], course_id, chapter_id, file.filename, ext, storage_path, file_size))
            mat_id = cursor.lastrowid
            
        # Process extraction immediately for seamless demo/testing
        process_material_file(mat_id)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, u.name as uploader_name,
                (SELECT COUNT(*) FROM extracted_chunks WHERE material_id = m.id) as chunks_count
                FROM materials m JOIN users u ON m.uploader_id = u.id
                WHERE m.id = ?
            """, (mat_id,))
            uploaded_records.append(dict(cursor.fetchone()))

    return uploaded_records

@app.get("/api/courses/{course_id}/materials", response_model=List[MaterialResponse])
def list_course_materials(course_id: int, user: dict = Depends(get_current_user)):
    verify_course_access(user, course_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, u.name as uploader_name,
            (SELECT COUNT(*) FROM extracted_chunks WHERE material_id = m.id) as chunks_count
            FROM materials m JOIN users u ON m.uploader_id = u.id
            WHERE m.course_id = ? AND m.visibility = 'course'
            ORDER BY m.created_at DESC
        """, (course_id,))
        return [dict(r) for r in cursor.fetchall()]

@app.post("/api/study-space/materials", response_model=List[MaterialResponse])
async def upload_personal_materials(
    personal_folder_id: Optional[int] = Form(None),
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user)
):
    require_student(user)
    if personal_folder_id:
        verify_folder_owner(user, personal_folder_id)

    uploaded_records = []
    for file in files:
        storage_path = save_uploaded_file(file)
        file_size = os.path.getsize(storage_path)
        ext = Path(file.filename).suffix.lower()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO materials (
                    uploader_id, course_id, chapter_id, personal_folder_id,
                    file_name, file_type, storage_path, file_size, visibility, extraction_status
                ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, 'private', 'pending')
            """, (user["id"], personal_folder_id, file.filename, ext, storage_path, file_size))
            mat_id = cursor.lastrowid

        process_material_file(mat_id)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, u.name as uploader_name,
                (SELECT COUNT(*) FROM extracted_chunks WHERE material_id = m.id) as chunks_count
                FROM materials m JOIN users u ON m.uploader_id = u.id
                WHERE m.id = ?
            """, (mat_id,))
            uploaded_records.append(dict(cursor.fetchone()))

    return uploaded_records

@app.get("/api/study-space/materials", response_model=List[MaterialResponse])
def list_personal_materials(folder_id: Optional[int] = Query(None), user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        if folder_id is not None:
            verify_folder_owner(user, folder_id)
            cursor.execute("""
                SELECT m.*, u.name as uploader_name,
                (SELECT COUNT(*) FROM extracted_chunks WHERE material_id = m.id) as chunks_count
                FROM materials m JOIN users u ON m.uploader_id = u.id
                WHERE m.uploader_id = ? AND m.visibility = 'private' AND m.personal_folder_id = ?
                ORDER BY m.created_at DESC
            """, (user["id"], folder_id))
        else:
            cursor.execute("""
                SELECT m.*, u.name as uploader_name,
                (SELECT COUNT(*) FROM extracted_chunks WHERE material_id = m.id) as chunks_count
                FROM materials m JOIN users u ON m.uploader_id = u.id
                WHERE m.uploader_id = ? AND m.visibility = 'private'
                ORDER BY m.created_at DESC
            """, (user["id"],))
        return [dict(r) for r in cursor.fetchall()]

@app.get("/api/materials/{material_id}")
def get_material_detail(material_id: int, user: dict = Depends(get_current_user)):
    mat = verify_material_access(user, material_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as chunks_count FROM extracted_chunks WHERE material_id = ?", (material_id,))
        mat["chunks_count"] = cursor.fetchone()["chunks_count"]
    return mat

@app.get("/api/materials/{material_id}/download")
def download_material(material_id: int, user: dict = Depends(get_current_user)):
    mat = verify_material_access(user, material_id)
    file_path = mat["storage_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File content missing on storage.")
    return FileResponse(file_path, filename=mat["file_name"])

@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int, user: dict = Depends(get_current_user)):
    mat = verify_material_access(user, material_id)
    # Check deletion ownership
    if mat["visibility"] == "course":
        verify_course_owner(user, mat["course_id"])
    else:
        if mat["uploader_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot delete another student's file.")

    # Remove storage file
    if os.path.exists(mat["storage_path"]):
        try:
            os.remove(mat["storage_path"])
        except Exception:
            pass

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
    return {"status": "ok", "message": "Material removed successfully."}

# -------------------------------------------------------------
# 5. AI Notes & Quick Revision Sheets (Generated Assets)
# -------------------------------------------------------------

@app.post("/api/ai/notes", response_model=StudyAssetResponse)
def create_ai_notes(req: AINotesRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    for mid in req.material_ids:
        verify_material_access(user, mid)

    res = generate_notes(req.material_ids, note_style=req.note_style, custom_focus=req.custom_focus)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO generated_assets (student_id, asset_type, title, content, source_material_ids)
            VALUES (?, 'notes', ?, ?, ?)
        """, (user["id"], res["title"], res["content"], json.dumps(req.material_ids)))
        asset_id = cursor.lastrowid
        cursor.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,))
        row = dict(cursor.fetchone())
        row["source_material_ids"] = json.loads(row["source_material_ids"])
        return row

@app.post("/api/ai/revision-sheet", response_model=StudyAssetResponse)
def create_ai_revision_sheet(req: AIRevisionSheetRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    for mid in req.material_ids:
        verify_material_access(user, mid)

    res = generate_revision_sheet(req.material_ids, title=req.title)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO generated_assets (student_id, asset_type, title, content, source_material_ids)
            VALUES (?, 'revision_sheet', ?, ?, ?)
        """, (user["id"], res["title"], res["content"], json.dumps(req.material_ids)))
        asset_id = cursor.lastrowid
        cursor.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,))
        row = dict(cursor.fetchone())
        row["source_material_ids"] = json.loads(row["source_material_ids"])

    # Update activity outside uncommitted block to prevent SQLite lock
    update_learning_activity(user["id"], "revised", "completed", material_id=req.material_ids[0])
    return row

@app.get("/api/study-assets", response_model=List[StudyAssetResponse])
def list_study_assets(asset_type: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        if asset_type:
            cursor.execute("SELECT * FROM generated_assets WHERE student_id = ? AND asset_type = ? ORDER BY updated_at DESC", (user["id"], asset_type))
        else:
            cursor.execute("SELECT * FROM generated_assets WHERE student_id = ? ORDER BY updated_at DESC", (user["id"],))
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r["source_material_ids"] = json.loads(r["source_material_ids"])
        return rows

@app.get("/api/study-assets/{asset_id}", response_model=StudyAssetResponse)
def get_study_asset(asset_id: int, user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Study asset not found.")
        row = dict(row)
        if row["student_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden: Asset belongs to another student.")
        row["source_material_ids"] = json.loads(row["source_material_ids"])
        return row

@app.patch("/api/study-assets/{asset_id}", response_model=StudyAssetResponse)
def update_study_asset(asset_id: int, req: StudyAssetUpdateRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM generated_assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Study asset not found.")
        if row["student_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden: Asset belongs to another student.")

        updates = []
        params = []
        if req.title is not None:
            updates.append("title = ?")
            params.append(req.title)
        if req.content is not None:
            updates.append("content = ?")
            params.append(req.content)
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(asset_id)
            cursor.execute(f"UPDATE generated_assets SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("SELECT * FROM generated_assets WHERE id = ?", (asset_id,))
        res = dict(cursor.fetchone())
        res["source_material_ids"] = json.loads(res["source_material_ids"])
        return res

# -------------------------------------------------------------
# 6. AI Tutor Q&A (Grounded Source Citations)
# -------------------------------------------------------------

@app.post("/api/ai/ask", response_model=AIAskResponse)
def ask_ai_tutor(req: AIAskRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    for mid in req.material_ids:
        verify_material_access(user, mid)
    return ask_tutor(req.question, req.material_ids)

# -------------------------------------------------------------
# 7. Quizzes and Grading
# -------------------------------------------------------------

@app.post("/api/ai/quizzes/generate", response_model=QuizDetailResponse)
def generate_new_quiz(req: QuizGenerateRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    material_ids = req.material_ids or []
    
    # Check if generated from asset
    if req.asset_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_material_ids FROM generated_assets WHERE id = ? AND student_id = ?", (req.asset_id, user["id"]))
            asset = cursor.fetchone()
            if asset:
                material_ids = json.loads(asset["source_material_ids"])

    for mid in material_ids:
        verify_material_access(user, mid)

    generated = generate_quiz(material_ids, question_count=req.question_count, question_types=req.question_types)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quizzes (student_id, title, source_description, source_material_ids, question_data)
            VALUES (?, ?, ?, ?, ?)
        """, (user["id"], generated["title"], generated["source_description"], json.dumps(material_ids), json.dumps(generated["questions"])))
        quiz_id = cursor.lastrowid

    # Strip answer_key and explanation from taking response
    client_questions = []
    for q in generated["questions"]:
        client_questions.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "options": q.get("options")
        })

    return QuizDetailResponse(
        id=quiz_id,
        title=generated["title"],
        source_description=generated["source_description"],
        total_questions=len(client_questions),
        questions=client_questions,
        created_at=str(uuid.uuid1())
    )

@app.get("/api/quizzes/{quiz_id}", response_model=QuizDetailResponse)
def get_quiz_for_taking(quiz_id: int, user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
        quiz = cursor.fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found.")
        quiz = dict(quiz)
        if quiz["student_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden: Quiz belongs to another student.")

        raw_questions = json.loads(quiz["question_data"])
        client_questions = [
            {"id": q["id"], "type": q["type"], "question": q["question"], "options": q.get("options")}
            for q in raw_questions
        ]
        return QuizDetailResponse(
            id=quiz["id"],
            title=quiz["title"],
            source_description=quiz["source_description"],
            total_questions=len(client_questions),
            questions=client_questions,
            created_at=str(quiz["created_at"])
        )

@app.post("/api/quizzes/{quiz_id}/attempts", response_model=QuizAttemptResponse)
def submit_quiz_attempt(quiz_id: int, req: QuizSubmitRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
        quiz = cursor.fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found.")
        quiz = dict(quiz)
        if quiz["student_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot take another student's quiz.")

        questions = json.loads(quiz["question_data"])
        submission_map = {ans.question_id: ans.submitted_answer for ans in req.answers}

        score = 0
        feedback_list = []
        for q in questions:
            qid = q["id"]
            user_ans = submission_map.get(qid)
            expected = q["answer_key"]
            is_correct = str(user_ans).strip().lower() == str(expected).strip().lower()
            if is_correct:
                score += 1

            feedback_list.append({
                "question_id": qid,
                "question": q["question"],
                "submitted_answer": user_ans,
                "correct_answer": expected,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "Reference from source text.")
            })

        total = len(questions)
        pct = round((score / total * 100), 1) if total > 0 else 0.0

        cursor.execute("""
            INSERT INTO quiz_attempts (student_id, quiz_id, score, total_questions, answers, feedback)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user["id"], quiz_id, score, total, json.dumps(submission_map), json.dumps(feedback_list)))
        attempt_id = cursor.lastrowid

        return QuizAttemptResponse(
            id=attempt_id,
            quiz_id=quiz_id,
            quiz_title=quiz["title"],
            student_id=user["id"],
            score=score,
            total_questions=total,
            percentage=pct,
            feedback=feedback_list,
            submitted_at=str(uuid.uuid1())
        )

@app.get("/api/quiz-attempts", response_model=List[QuizAttemptResponse])
def list_quiz_attempts(user: dict = Depends(get_current_user)):
    require_student(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT qa.*, q.title as quiz_title
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            WHERE qa.student_id = ?
            ORDER BY qa.submitted_at DESC
        """, (user["id"],))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            pct = round((d["score"] / d["total_questions"] * 100), 1) if d["total_questions"] > 0 else 0.0
            results.append(QuizAttemptResponse(
                id=d["id"],
                quiz_id=d["quiz_id"],
                quiz_title=d["quiz_title"],
                student_id=d["student_id"],
                score=d["score"],
                total_questions=d["total_questions"],
                percentage=pct,
                feedback=json.loads(d["feedback"]),
                submitted_at=str(d["submitted_at"])
            ))
        return results

# -------------------------------------------------------------
# 8. YouTube Video Recommendations
# -------------------------------------------------------------

@app.post("/api/ai/video-recommendations", response_model=VideoRecommendationsResponse)
def get_video_recommendations_endpoint(req: AINotesRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    for mid in req.material_ids:
        verify_material_access(user, mid)
    res = get_video_recommendations(req.material_ids)
    return VideoRecommendationsResponse(**res)

# -------------------------------------------------------------
# 9. Learning Activities & Progress Tracking
# -------------------------------------------------------------

@app.put("/api/learning-activities")
def update_activity(req: LearningActivityUpdateRequest, user: dict = Depends(get_current_user)):
    require_student(user)
    if req.material_id:
        verify_material_access(user, req.material_id)
    update_learning_activity(
        student_id=user["id"],
        activity_type=req.activity_type,
        status=req.status,
        material_id=req.material_id,
        chapter_id=req.chapter_id,
        course_id=req.course_id
    )
    return {"status": "ok", "message": "Learning activity updated."}

@app.get("/api/progress/summary", response_model=ProgressSummaryResponse)
def get_progress_summary(user: dict = Depends(get_current_user)):
    require_student(user)
    summary = get_student_progress_summary(user["id"])
    return ProgressSummaryResponse(**summary)

# Mount frontend directory for full web UI access
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def index_redirect():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9000))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
