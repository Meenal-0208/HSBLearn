"""
HSBLearn Automated Backend End-to-End Test Suite.
Validates authentication, role enforcement, private study space isolation,
document text extraction, AI study aids, quizzes, and learning progress metrics.
"""
import unittest
import os
import io
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, seed_demo_data, get_db

class TestHSBLearn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        # Register clean test accounts for the test runner
        cls.client.post("/api/auth/register", json={
            "name": "Dr. Alex Morgan", "email": "instructor@hsblearn.local", "password": "instructor123", "role": "instructor"
        })
        cls.client.post("/api/auth/register", json={
            "name": "Maya Lin", "email": "student@hsblearn.local", "password": "student123", "role": "student"
        })
        cls.client.post("/api/auth/register", json={
            "name": "James Reed", "email": "student2@hsblearn.local", "password": "student123", "role": "student"
        })

    def test_01_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_02_auth_login(self):
        # Test valid student login
        res = self.client.post("/api/auth/login", json={
            "email": "student@hsblearn.local",
            "password": "student123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "student")

        # Test invalid password
        res_bad = self.client.post("/api/auth/login", json={
            "email": "student@hsblearn.local",
            "password": "wrongpassword"
        })
        self.assertEqual(res_bad.status_code, 401)

    def test_03_permissions_isolation(self):
        # Login as student 1
        res1 = self.client.post("/api/auth/login", json={
            "email": "student@hsblearn.local",
            "password": "student123"
        })
        token1 = res1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Student 1 creates private folder
        res_f = self.client.post("/api/study-space/folders", headers=headers1, json={"name": "Confidential Research"})
        self.assertEqual(res_f.status_code, 200)
        folder_id = res_f.json()["id"]

        # Student 2 attempts to delete Student 1's folder -> must return 403
        res2 = self.client.post("/api/auth/login", json={
            "email": "student2@hsblearn.local",
            "password": "student123"
        })
        token2 = res2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        res_hack = self.client.delete(f"/api/study-space/folders/{folder_id}", headers=headers2)
        self.assertEqual(res_hack.status_code, 403)

    def test_04_instructor_role_enforcement(self):
        # Student tries to create course -> must return 403
        res = self.client.post("/api/auth/login", json={
            "email": "student@hsblearn.local",
            "password": "student123"
        })
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res_course = self.client.post("/api/courses", headers=headers, json={"title": "Hacked Course"})
        self.assertEqual(res_course.status_code, 403)

    def test_05_upload_extract_and_ai_workflow(self):
        # 1. Login as instructor and upload a text lecture
        res_inst = self.client.post("/api/auth/login", json={
            "email": "instructor@hsblearn.local",
            "password": "instructor123"
        })
        inst_token = res_inst.json()["access_token"]
        inst_headers = {"Authorization": f"Bearer {inst_token}"}

        # Create course
        res_c = self.client.post("/api/courses", headers=inst_headers, json={
            "title": "Computer Systems", "description": "Intro to Systems"
        })
        self.assertEqual(res_c.status_code, 200)
        course_id = res_c.json()["id"]

        # Upload material into created course
        sample_content = b"Computer Operating Systems. Virtual memory provides an illusion of large contiguous memory to programs. It maps virtual pages to physical frames via the page table."
        files = [('files', ('lecture1.txt', sample_content, 'text/plain'))]
        
        res_up = self.client.post(
            f"/api/courses/{course_id}/materials",
            headers=inst_headers,
            files=files
        )
        self.assertEqual(res_up.status_code, 200)
        mat_records = res_up.json()
        self.assertEqual(len(mat_records), 1)
        material_id = mat_records[0]["id"]
        self.assertEqual(mat_records[0]["extraction_status"], "ready")

        # 2. Login as student 1 (enrolled in course 1)
        res_st = self.client.post("/api/auth/login", json={
            "email": "student@hsblearn.local",
            "password": "student123"
        })
        st_token = res_st.json()["access_token"]
        st_headers = {"Authorization": f"Bearer {st_token}"}

        # Student generates AI notes
        res_notes = self.client.post("/api/ai/notes", headers=st_headers, json={
            "material_ids": [material_id],
            "note_style": "detailed"
        })
        self.assertEqual(res_notes.status_code, 200)
        self.assertIn("content", res_notes.json())

        # Student generates Quick Revision Sheet
        res_rev = self.client.post("/api/ai/revision-sheet", headers=st_headers, json={
            "material_ids": [material_id]
        })
        self.assertEqual(res_rev.status_code, 200)

        # Student asks AI tutor with grounded citation check
        res_tutor = self.client.post("/api/ai/ask", headers=st_headers, json={
            "question": "What does virtual memory provide?",
            "material_ids": [material_id]
        })
        self.assertEqual(res_tutor.status_code, 200)
        tutor_data = res_tutor.json()
        self.assertTrue(tutor_data["is_grounded"])
        self.assertTrue(len(tutor_data["citations"]) > 0)

        # Student generates and submits a Quiz
        res_quiz = self.client.post("/api/ai/quizzes/generate", headers=st_headers, json={
            "material_ids": [material_id],
            "question_count": 2,
            "question_types": ["mcq"]
        })
        self.assertEqual(res_quiz.status_code, 200)
        quiz_id = res_quiz.json()["id"]

        # Submit attempt
        res_sub = self.client.post(f"/api/quizzes/{quiz_id}/attempts", headers=st_headers, json={
            "answers": [{"question_id": 1, "submitted_answer": "virtual"}]
        })
        self.assertEqual(res_sub.status_code, 200)
        attempt_data = res_sub.json()
        self.assertIn("score", attempt_data)
        self.assertIn("feedback", attempt_data)

        # Mark material as completed
        res_act = self.client.put("/api/learning-activities", headers=st_headers, json={
            "activity_type": "read",
            "status": "completed",
            "material_id": material_id
        })
        self.assertEqual(res_act.status_code, 200)

        # Check progress summary
        res_prog = self.client.get("/api/progress/summary", headers=st_headers)
        self.assertEqual(res_prog.status_code, 200)
        prog_data = res_prog.json()
        self.assertGreaterEqual(prog_data["completed_materials"], 1)
        self.assertGreaterEqual(prog_data["total_quizzes_taken"], 1)
        self.assertGreaterEqual(prog_data["revision_sessions_count"], 1)

if __name__ == "__main__":
    unittest.main()
