"""
Server-side Permission Checks & Ownership Enforcements.
Never relies on client-side route hiding.
"""
from fastapi import HTTPException, status
from backend.database import get_db

def require_role(user: dict, required_role: str):
    """Enforces that the authenticated user possesses the required role."""
    if user.get("role") != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Requires '{required_role}' role."
        )

def require_instructor(user: dict):
    require_role(user, "instructor")

def require_student(user: dict):
    require_role(user, "student")

def verify_course_owner(user: dict, course_id: int):
    """Verifies that an instructor owns the course."""
    require_instructor(user)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT instructor_id FROM courses WHERE id = ?", (course_id,))
        course = cursor.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found.")
        if course["instructor_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this course."
            )

def verify_course_access(user: dict, course_id: int):
    """
    Checks that the user is either the instructor who owns the course,
    or a student with active access/enrollment.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT instructor_id FROM courses WHERE id = ?", (course_id,))
        course = cursor.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found.")

        if user["role"] == "instructor":
            if course["instructor_id"] != user["id"]:
                raise HTTPException(status_code=403, detail="Instructor is not assigned to this course.")
            return

        # For students: all published courses are accessible in the Shared Classroom
        if course["status"] == "published":
            return

        # Check explicit access if draft/restricted
        cursor.execute(
            "SELECT status FROM course_access WHERE course_id = ? AND student_id = ?",
            (course_id, user["id"])
        )
        access = cursor.fetchone()
        if not access or access["status"] != "active":
            raise HTTPException(status_code=403, detail="You do not have access to this course.")

def verify_folder_owner(user: dict, folder_id: int):
    """Ensures personal study space folders can only be accessed by the owner student."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM personal_folders WHERE id = ?", (folder_id,))
        folder = cursor.fetchone()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found.")
        if folder["student_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden: You do not own this personal folder.")

def verify_material_access(user: dict, material_id: int) -> dict:
    """
    Verifies permission for reading/downloading a material:
    - If course material: user must have active course access or be instructor owner.
    - If personal material: user must be the uploader.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, c.instructor_id
            FROM materials m
            LEFT JOIN courses c ON m.course_id = c.id
            WHERE m.id = ?
        """, (material_id,))
        mat = cursor.fetchone()
        if not mat:
            raise HTTPException(status_code=404, detail="Material not found.")
        mat = dict(mat)

        if mat["visibility"] == "course":
            if user["role"] == "instructor" and mat["instructor_id"] == user["id"]:
                return mat
            # If student: all materials in published courses are accessible
            cursor.execute("SELECT status FROM courses WHERE id = ?", (mat["course_id"],))
            c_info = cursor.fetchone()
            if c_info and c_info["status"] == "published":
                return mat

            # Check explicit student enrollment if restricted
            cursor.execute(
                "SELECT status FROM course_access WHERE course_id = ? AND student_id = ?",
                (mat["course_id"], user["id"])
            )
            acc = cursor.fetchone()
            if not acc or acc["status"] != "active":
                raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this course material.")
            return mat
        else:
            # Private material
            if mat["uploader_id"] != user["id"]:
                raise HTTPException(status_code=403, detail="Forbidden: Private material belongs to another student.")
            return mat
