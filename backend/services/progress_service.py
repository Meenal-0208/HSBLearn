"""
HSBLearn Learning Activity & Progress Metrics Calculation Service.
Separates Content Coverage, Quiz Performance, and Revision Sessions.
Never fabricates progress or labels content completion as mastery.
"""
from typing import Dict, Any, List
from backend.database import get_db

def update_learning_activity(
    student_id: int,
    activity_type: str,
    status: str,
    material_id: int = None,
    chapter_id: int = None,
    course_id: int = None
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO learning_activities (student_id, activity_type, status, material_id, chapter_id, course_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id, activity_type, material_id, chapter_id, course_id)
            DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP;
        """, (student_id, activity_type, status, material_id, chapter_id, course_id))

def get_student_progress_summary(student_id: int) -> Dict[str, Any]:
    """
    Computes genuine progress from stored records:
    1. Content Coverage: Completed materials / total accessible materials
    2. Quiz Performance: Average score % and total attempts
    3. Revision sessions count: completed revision activities
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Accessible materials (all published course materials + private personal files)
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as count
            FROM materials m
            LEFT JOIN courses c ON m.course_id = c.id
            WHERE (m.visibility = 'course' AND c.status = 'published')
               OR (m.visibility = 'private' AND m.uploader_id = ?)
        """, (student_id,))
        total_accessible = cursor.fetchone()["count"] or 0

        # Completed materials
        cursor.execute("""
            SELECT COUNT(DISTINCT material_id) as count
            FROM learning_activities
            WHERE student_id = ? AND activity_type = 'read' AND status = 'completed' AND material_id IS NOT NULL
        """, (student_id,))
        completed_mats = cursor.fetchone()["count"] or 0

        coverage_pct = round((completed_mats / total_accessible * 100), 1) if total_accessible > 0 else 0.0

        # 2. Quiz Performance
        cursor.execute("""
            SELECT COUNT(*) as total_attempts, AVG((score / total_questions) * 100) as avg_pct
            FROM quiz_attempts
            WHERE student_id = ?
        """, (student_id,))
        quiz_stats = cursor.fetchone()
        total_quizzes = quiz_stats["total_attempts"] or 0
        avg_score = round(quiz_stats["avg_pct"], 1) if quiz_stats["avg_pct"] is not None else 0.0

        # 3. Revision Activity
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM learning_activities
            WHERE student_id = ? AND activity_type = 'revised' AND status = 'completed'
        """, (student_id,))
        revision_count = cursor.fetchone()["count"] or 0

        # 4. Recent activities
        cursor.execute("""
            SELECT activity_type, status, updated_at, material_id, chapter_id, course_id
            FROM learning_activities
            WHERE student_id = ?
            ORDER BY updated_at DESC
            LIMIT 5
        """, (student_id,))
        recent = [dict(r) for r in cursor.fetchall()]

        return {
            "student_id": student_id,
            "total_materials_accessible": total_accessible,
            "completed_materials": completed_mats,
            "content_coverage_pct": coverage_pct,
            "total_quizzes_taken": total_quizzes,
            "average_quiz_score_pct": avg_score,
            "revision_sessions_count": revision_count,
            "recent_activities": recent
        }
