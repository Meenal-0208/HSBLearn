"""
Pydantic Request and Response Schemas for HSBLearn API.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- Auth & User ---
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=6)
    role: str = Field("student", pattern="^(student|instructor)$")

class UserLoginRequest(BaseModel):
    email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Course ---
class CourseCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = ""

class CourseUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")

class CourseResponse(BaseModel):
    id: int
    title: str
    description: str
    instructor_id: int
    instructor_name: Optional[str] = None
    status: str
    created_at: str
    updated_at: Optional[str] = None
    total_chapters: Optional[int] = 0
    total_materials: Optional[int] = 0

class CourseAccessRequest(BaseModel):
    student_email: Optional[str] = None
    student_id: Optional[int] = None

# --- Chapter ---
class ChapterCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = ""
    order_index: Optional[int] = 0

class ChapterResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: str
    order_index: int
    created_at: str

# --- Folder (Study Space) ---
class FolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_folder_id: Optional[int] = None

class FolderUpdateRequest(BaseModel):
    name: Optional[str] = None
    parent_folder_id: Optional[int] = None

class FolderResponse(BaseModel):
    id: int
    student_id: int
    parent_folder_id: Optional[int]
    name: str
    created_at: str
    subfolders_count: Optional[int] = 0
    materials_count: Optional[int] = 0

# --- Material ---
class MaterialResponse(BaseModel):
    id: int
    uploader_id: int
    uploader_name: Optional[str] = None
    course_id: Optional[int]
    chapter_id: Optional[int]
    personal_folder_id: Optional[int]
    file_name: str
    file_type: str
    file_size: int
    visibility: str
    extraction_status: str
    extracted_text_status: Optional[str] = ""
    created_at: str
    chunks_count: Optional[int] = 0

# --- AI Notes & Revision ---
class AINotesRequest(BaseModel):
    material_ids: List[int] = Field(..., min_items=1)
    note_style: str = Field("detailed", pattern="^(concise|detailed)$")
    custom_focus: Optional[str] = None

class AIRevisionSheetRequest(BaseModel):
    material_ids: List[int] = Field(..., min_items=1)
    title: Optional[str] = None

class StudyAssetResponse(BaseModel):
    id: int
    student_id: int
    asset_type: str
    title: str
    content: str
    source_material_ids: List[int]
    created_at: str
    updated_at: str

class StudyAssetUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# --- AI Tutor Q&A ---
class AIAskRequest(BaseModel):
    question: str = Field(..., min_length=2)
    material_ids: List[int] = Field(..., min_items=1)

class SourceCitation(BaseModel):
    material_id: int
    material_name: str
    page_or_slide: Optional[int] = None
    snippet: str

class AIAskResponse(BaseModel):
    question: str
    answer: str
    is_grounded: bool
    citations: List[SourceCitation]

# --- Quizzes & Attempts ---
class QuizGenerateRequest(BaseModel):
    material_ids: Optional[List[int]] = None
    asset_id: Optional[int] = None # Or generate from saved AI notes/revision
    question_count: int = Field(5, ge=1, le=20)
    question_types: List[str] = Field(["mcq"], description="mcq, true_false, short_answer")

class QuizQuestion(BaseModel):
    id: int
    type: str # mcq, true_false, short_answer
    question: str
    options: Optional[List[str]] = None
    # correct answer and explanation hidden during taking, exposed after grading

class QuizDetailResponse(BaseModel):
    id: int
    title: str
    source_description: str
    total_questions: int
    questions: List[QuizQuestion]
    created_at: str

class QuestionAnswerSubmission(BaseModel):
    question_id: int
    submitted_answer: Any

class QuizSubmitRequest(BaseModel):
    answers: List[QuestionAnswerSubmission]

class QuestionFeedback(BaseModel):
    question_id: int
    question: str
    submitted_answer: Any
    correct_answer: Any
    is_correct: bool
    explanation: str

class QuizAttemptResponse(BaseModel):
    id: int
    quiz_id: int
    quiz_title: Optional[str] = None
    student_id: int
    score: float
    total_questions: int
    percentage: float
    feedback: List[QuestionFeedback]
    submitted_at: str

# --- YouTube Recommendations ---
class VideoRecommendationItem(BaseModel):
    title: str
    channel: str
    url: str
    duration: Optional[str] = None
    relevance_reason: str
    source_topic: str

class VideoRecommendationsResponse(BaseModel):
    configured: bool
    message: Optional[str] = None
    recommendations: List[VideoRecommendationItem]

# --- Learning Activities & Progress ---
class LearningActivityUpdateRequest(BaseModel):
    activity_type: str = Field(..., pattern="^(read|watched|completed|revised)$")
    status: str = Field(..., pattern="^(not_started|in_progress|completed)$")
    material_id: Optional[int] = None
    chapter_id: Optional[int] = None
    course_id: Optional[int] = None

class ProgressSummaryResponse(BaseModel):
    student_id: int
    total_materials_accessible: int
    completed_materials: int
    content_coverage_pct: float
    total_quizzes_taken: int
    average_quiz_score_pct: float
    revision_sessions_count: int
    recent_activities: List[Dict[str, Any]]
