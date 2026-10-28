"""
HSBLearn SQLite Database Layer & Schema Management.
"""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# Default database location inside data/ directory (or /tmp on serverless environments like Vercel)
BASE_DIR = Path(__file__).resolve().parent.parent

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if os.getenv("VERCEL"):
    DATA_DIR = Path("/tmp/data")
    DB_PATH = Path("/tmp/hsblearn.db")
else:
    DATA_DIR = BASE_DIR / "data"
    DB_PATH = DATA_DIR / "hsblearn.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

class LibsqlRow:
    """Provides sqlite3.Row-like dictionary and index access for libsql rows."""
    def __init__(self, cols, values):
        self._d = dict(zip(cols, values))
        self._v = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._d[key]
        return self._v[key]

    def get(self, key, default=None):
        return self._d.get(key, default)

    def keys(self):
        return self._d.keys()

    def values(self):
        return self._d.values()

    def items(self):
        return self._d.items()

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._v)

    def __repr__(self):
        return repr(self._d)

class LibsqlCursorWrapper:
    """Wraps a libsql cursor to return LibsqlRow instances with dict-like access."""
    def __init__(self, cursor):
        self._cur = cursor

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

    @property
    def rowcount(self):
        return getattr(self._cur, "rowcount", -1)

    @property
    def description(self):
        return self._cur.description

    def execute(self, sql, params=()):
        self._cur.execute(sql, params)
        return self

    def executemany(self, sql, seq_of_params):
        self._cur.executemany(sql, seq_of_params)
        return self

    def executescript(self, sql_script):
        if hasattr(self._cur, "executescript"):
            return self._cur.executescript(sql_script)
        for stmt in sql_script.split(";"):
            stmt = stmt.strip()
            if stmt:
                self._cur.execute(stmt)
        return self

    def _wrap_row(self, row):
        if row is None:
            return None
        cols = [c[0] for c in self._cur.description] if self._cur.description else []
        return LibsqlRow(cols, row)

    def fetchone(self):
        row = self._cur.fetchone()
        return self._wrap_row(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [c[0] for c in self._cur.description] if self._cur.description else []
        return [LibsqlRow(cols, r) for r in rows]

class LibsqlConnectionWrapper:
    """Wraps a libsql connection to provide standard sqlite3 cursor and commit semantics."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return LibsqlCursorWrapper(self._conn.cursor())

    def execute(self, sql, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        if hasattr(self._conn, "rollback"):
            self._conn.rollback()

    def close(self):
        self._conn.close()

def get_db_connection():
    """
    Returns an SQLite or LibSQL connection configured with row access
    and foreign key constraints enabled.
    """
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        import libsql
        conn = libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        return LibsqlConnectionWrapper(conn)

    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    """
    Context manager yielding a transactional SQLite connection.
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """
    Initializes database tables, indexes, and constraints as defined in the PRD.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ('student', 'instructor')) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")

        # Password Resets table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pwd_resets_token ON password_resets(token);")

        # 2. Courses table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            instructor_id INTEGER NOT NULL,
            status TEXT CHECK(status IN ('draft', 'published', 'archived')) DEFAULT 'published',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_instructor ON courses(instructor_id);")

        # 3. Course Access / Enrollment table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT CHECK(status IN ('active', 'suspended')) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id, student_id),
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_course_access_student ON course_access(student_id);")

        # 4. Chapters table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            order_index INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_course ON chapters(course_id);")

        # 5. Personal Folders (My Study Space)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS personal_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            parent_folder_id INTEGER,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_folder_id) REFERENCES personal_folders(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_folders_student ON personal_folders(student_id);")

        # 6. Materials (Shared Course or Personal Uploads)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploader_id INTEGER NOT NULL,
            course_id INTEGER,
            chapter_id INTEGER,
            personal_folder_id INTEGER,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            visibility TEXT CHECK(visibility IN ('course', 'private')) DEFAULT 'private',
            extraction_status TEXT CHECK(extraction_status IN ('pending', 'processing', 'ready', 'failed', 'unavailable')) DEFAULT 'pending',
            extracted_text_status TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL,
            FOREIGN KEY (personal_folder_id) REFERENCES personal_folders(id) ON DELETE SET NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_course ON materials(course_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_uploader ON materials(uploader_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_folder ON materials(personal_folder_id);")

        # 7. Extracted Chunks (for RAG / AI grounding)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            page_or_slide INTEGER,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_material ON extracted_chunks(material_id);")

        # 8. Generated Assets (AI Notes & Revision Sheets)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            asset_type TEXT CHECK(asset_type IN ('notes', 'revision_sheet')) NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source_material_ids TEXT NOT NULL, -- JSON array of material IDs
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_student ON generated_assets(student_id);")

        # 9. Quizzes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            source_description TEXT DEFAULT '',
            source_material_ids TEXT DEFAULT '[]', -- JSON array of material IDs
            question_data TEXT NOT NULL, -- JSON array of questions, options, answer_key, explanation
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quizzes_student ON quizzes(student_id);")

        # 10. Quiz Attempts
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            quiz_id INTEGER NOT NULL,
            score REAL NOT NULL,
            total_questions INTEGER NOT NULL,
            answers TEXT NOT NULL, -- JSON array/object of submitted answers
            feedback TEXT NOT NULL, -- JSON feedback details
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_attempts_student ON quiz_attempts(student_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);")

        # 11. Learning Activities (Progress Tracking)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            material_id INTEGER,
            chapter_id INTEGER,
            course_id INTEGER,
            activity_type TEXT CHECK(activity_type IN ('read', 'watched', 'completed', 'revised')) NOT NULL,
            status TEXT CHECK(status IN ('not_started', 'in_progress', 'completed')) DEFAULT 'not_started',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, activity_type, material_id, chapter_id, course_id),
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_student ON learning_activities(student_id);")

def seed_demo_data():
    """
    Seeds authorized student logins (2026mbapm001@hsb.edu.in to 2026mbapm039@hsb.edu.in)
    and instructor logins (amanraj@hsb.edu.in, kusum@hsb.edu.in) with default password '123456'.
    """
    import hashlib
    default_password_hash = hashlib.sha256(b"hsblearn_salt_123456").hexdigest()

    # Pre-authorized Instructors
    instructors = [
        ("Prof. Aman Raj", "amanraj@hsb.edu.in"),
        ("Prof. Kusum", "kusum@hsb.edu.in")
    ]

    # Pre-authorized Students: 2026mbapm001 to 2026mbapm039
    students = [
        (f"Student {i:03d}", f"2026mbapm{i:03d}@hsb.edu.in")
        for i in range(1, 40)
    ]

    with get_db() as conn:
        cursor = conn.cursor()

        for name, email in instructors:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (?, ?, ?, 'instructor')
                """, (name, email, default_password_hash))

        for name, email in students:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (?, ?, ?, 'student')
                """, (name, email, default_password_hash))

if __name__ == "__main__":
    init_db()
    print("HSBLearn SQLite database initialized cleanly without dummy records.")
