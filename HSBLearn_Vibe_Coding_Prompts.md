# HSBLearn — Vibe-Coding Prompts
**Tool:** Google Antigravity  
**Product:** AI-native Learning Management & Personal Study Platform  
**MVP stack:** HTML + Tailwind CSS + JavaScript · Python + FastAPI · SQLite · Postman  
**AI integrations:** Server-side LLM provider adapter; real YouTube search/API integration when credentials are configured

---

## How to use this file

Each numbered step is one prompt block. Paste **one prompt at a time** into Antigravity in the `hsblearn` project folder. Let the agent finish, run the app, inspect the result, and test the stated acceptance checks before moving on. Do not paste all prompts at once.

The goal is a working, inspectable MVP—not a large unreviewed code dump. Ask Antigravity to explain any file or function you do not understand. Keep credentials in backend environment variables, never in frontend code or source control.

## Product rules that apply to every step

- There are two roles: **Student** and **Instructor**.
- The **Shared Classroom** contains instructor-uploaded materials accessible to students who have access to that course.
- **My Study Space** is private to each student by default.
- The AI can operate on instructor materials, personal uploads, or a combination the student explicitly selects.
- Completion status is not the same as mastery. Track material completion, quiz performance, and revision activity separately.
- Enforce permissions on the backend for every private file, course, generated asset, quiz attempt, and progress record.
- Never fabricate AI outputs, source citations, YouTube videos, progress values, or quiz results.
- Build loading, error, empty, and success states for network-backed screens.
- Use a provider-agnostic server-side AI service so the LLM provider can be changed without rewriting the app.

---

## Step 0 — Create the project structure

```text
Create a new project called "hsblearn" with this structure:

hsblearn/
  backend/
    __init__.py
    main.py
    database.py
    models.py
    auth.py
    permissions.py
    services/
      __init__.py
      document_service.py
      ai_service.py
      youtube_service.py
      progress_service.py
  frontend/
    index.html
    student.html
    instructor.html
    course.html
    study-space.html
    material.html
    quiz.html
    progress.html
    js/
      app.js
      student.js
      instructor.js
      course.js
      study-space.js
      material.js
      quiz.js
      progress.js
  uploads/
  data/
  tests/
  .env.example
  .gitignore
  requirements.txt
  README.md

Use Python with a virtual environment. Add FastAPI, uvicorn, pydantic, python-multipart, itsdangerous or an appropriate session/auth library, and document extraction libraries needed for PDF, DOCX, and PPTX (for example pypdf, python-docx, python-pptx). Add the SQLite/database dependency only if needed by the chosen implementation.

Keep files mostly empty apart from requirements and basic app setup. Do not implement all features yet. Confirm the structure and give me the exact commands to create/activate the virtual environment on Windows PowerShell.
```

**Check before Step 1:** the structure exists, dependencies install, and `.env` is ignored by Git. Create a local `.env` from `.env.example` only when secrets are needed.

---

## Step 1 — Database schema and persistence

```text
Implement SQLite persistence in backend/database.py. Use a local hsblearn.db for the prototype. Create tables with sensible primary keys, foreign keys, timestamps, and indexes for these logical entities:

1. users: id, name, email (unique), password_hash or auth provider ID, role (student/instructor), created_at.
2. courses: id, title, description, instructor_id, status, created_at, updated_at.
3. course_access: id, course_id, student_id, status, created_at; unique course/student pair.
4. chapters: id, course_id, title, description, order_index, created_at.
5. personal_folders: id, student_id, parent_folder_id nullable, name, created_at.
6. materials: id, uploader_id, course_id nullable, chapter_id nullable, personal_folder_id nullable, file_name, file_type, storage_path, visibility, extraction_status, extracted_text_status, created_at.
7. extracted_chunks: id, material_id, page_or_slide nullable, chunk_index, text.
8. generated_assets: id, student_id, asset_type (notes/revision_sheet), title, content, source_material_ids stored in a maintainable form, created_at, updated_at.
9. quizzes: id, student_id, title, source description, question data or related quiz_questions table, created_at.
10. quiz_attempts and attempt_answers: student_id, quiz_id, score, total_questions, submitted_at, answers and feedback.
11. learning_activities: id, student_id, material_id nullable, chapter_id nullable, activity_type (read/watched/completed/revised), status, updated_at.
12. ai_interactions or recommendations only if needed for the MVP.

Add a get_db_connection() helper and database initialization function. Use parameterised SQL. Enforce foreign keys. Do not store file bytes directly in SQLite; store file paths/keys and metadata.

Important: model ownership and course access explicitly. A student must not be able to read another student's private folders or files. Avoid storing a single generic progress percentage as the source of truth; compute metrics from activity and attempt records.

Create a small development seed script with clearly labelled demo users and a sample course. Do not silently create production credentials or hardcode real secrets. Run initialization and show the tables created.
```

**Test:** restart the server and confirm the sample course and records persist.

---

## Step 2 — Pydantic models and API contract

```text
In backend/models.py, define request and response models for:
- User registration/login and user summary (never return password hashes).
- Course create/update/output.
- Course access/enrollment.
- Chapter create/update/output.
- Folder create/update/output.
- Material metadata/output and upload result.
- Learning activity updates.
- AI notes request/result.
- Revision sheet request/result.
- Quiz generation request, quiz output, quiz submission, and attempt summary.
- AI tutor question/answer with source references.
- YouTube recommendation output.
- Student progress summary and topic-level progress.

Use type hints, validation, and clear optional fields. Make API response shapes consistent and document them. Define errors in a consistent format, with appropriate HTTP status codes. Do not accept student_id or instructor_id from a client as proof of identity; derive the current user from the authenticated session/token on the server.
```

**Test:** inspect FastAPI `/docs` and confirm request and response schemas are readable.

---

## Step 3 — Authentication, roles, and permissions

```text
Implement a beginner-friendly but server-enforced authentication flow in backend/auth.py and backend/permissions.py.

Requirements:
1. Provide registration/login/logout or an equivalent session flow appropriate for this local prototype.
2. Store passwords only as secure password hashes if password login is implemented; never store plaintext passwords.
3. Roles are student and instructor.
4. Protect API routes with a current-user dependency.
5. Instructor routes must verify that the instructor owns or is assigned to the course.
6. Student routes must verify access to the course before returning shared course material.
7. Personal folders, private materials, generated notes, quiz attempts, and learning activity are visible only to their owner by default.
8. Do not rely on frontend route hiding as security.
9. Add clear 401 and 403 responses and test unauthorized access.
10. Keep any development/demo accounts clearly labelled and never use predictable credentials in production.

If a full production auth provider is not configured, document the local prototype limitation in README. Do not claim the prototype is production-ready.
```

**Test:** a student cannot call an instructor endpoint, and one student's private file cannot be opened by another student.

---

## Step 4 — Course and instructor material APIs

```text
Implement course, chapter, course-access, and instructor material APIs in backend/main.py or a router module.

Suggested endpoints:
- GET /api/me
- GET /api/courses
- POST /api/courses (instructor only)
- GET /api/courses/{course_id}
- PATCH /api/courses/{course_id} (owner instructor only)
- POST /api/courses/{course_id}/chapters (owner instructor only)
- GET /api/courses/{course_id}/chapters
- POST /api/courses/{course_id}/access (restricted instructor/admin action for this MVP)
- GET /api/courses/{course_id}/materials
- POST /api/courses/{course_id}/materials (instructor only)
- GET /api/materials/{material_id}
- DELETE /api/materials/{material_id} (owner/authorized instructor or personal owner only)

Use consistent response models, server-side validation, and permissions. Course materials must be visible to students with course access, not to every logged-in user. Include pagination or sensible result limits where appropriate. Keep route names and request/response contracts documented.
```

**Test:** instructor creates a course and chapter; an authorised student can list its published materials; an unrelated student receives 403/404 without learning private details.

---

## Step 5 — Student My Study Space and bulk upload

```text
Build My Study Space APIs and UI.

Features:
1. Each student gets a private workspace.
2. Create, rename, move, and delete folders, including nested subject/chapter folders.
3. Support multi-file upload for PDF, PPTX, DOCX, and TXT where extraction is supported.
4. Validate file type and size on the backend; create safe server-generated storage names to avoid path traversal and filename collisions.
5. Store metadata and the file's private storage path; do not expose arbitrary filesystem paths to the browser.
6. Show per-file upload status, progress where practical, file type, size, and processing status.
7. Let the student confirm or change the destination folder after upload.
8. Show clear errors for unsupported, corrupt, encrypted, oversized, or failed uploads.
9. Ensure students can only list, open, move, or delete their own private files.

Suggested endpoints:
- GET /api/study-space/folders
- POST /api/study-space/folders
- PATCH /api/study-space/folders/{folder_id}
- DELETE /api/study-space/folders/{folder_id}
- GET /api/study-space/materials
- POST /api/study-space/materials (multipart upload; support multiple files)
- GET /api/materials/{material_id}/download or a safe authenticated preview endpoint

Do not silently treat a failed upload as successful.
```

**Test:** upload several files together, refresh, and confirm the files remain in the correct private folder.

---

## Step 6 — Extract text and prepare material for AI

```text
Implement backend/services/document_service.py.

Requirements:
1. Extract text from supported PDF, DOCX, PPTX, and TXT files.
2. Preserve page numbers for PDFs and slide numbers for PPTX wherever the library permits.
3. Save extraction status and chunk extracted text into manageable passages linked to the source material.
4. Handle scanned PDFs or files with no extractable text with a clear "text extraction unavailable" status; do not pretend OCR was performed.
5. Handle corrupt/password-protected files without crashing the server.
6. Add a processing status so the UI can show queued/processing/ready/failed.
7. Keep file access permission checks in place before processing or returning content.
8. Avoid printing entire student documents or sensitive content into logs.
9. Include a simple test for each supported file type and one failure case.

Use chunks and metadata that can later support retrieval-augmented generation (RAG). Do not add a vector database unless the MVP genuinely needs it; start with a simple retrieval strategy and keep it replaceable.
```

**Test:** upload a PDF, PPTX, and DOCX; verify extracted text and source locations are associated with the correct material.

---

## Step 7 — AI service foundation and AI-generated notes

```text
Implement backend/services/ai_service.py as a provider-agnostic server-side service.

Requirements:
1. Read LLM credentials from environment variables only. Never put secrets in frontend code, Git, or API responses.
2. Add a clear "AI not configured" response when credentials are absent; the rest of the LMS must still work.
3. Accept selected material IDs and verify that the current user has permission to access each source.
4. Use extracted text, chunks, and source metadata to generate notes grounded in the chosen files.
5. Offer at least two note styles: concise notes and detailed explanatory notes. Include important definitions, examples, and headings when supported by the source.
6. Do not invent content as if it came from the source. Mark uncertain or missing information clearly.
7. Save the result as a generated asset with source material references.
8. Allow users to reopen, edit, and regenerate notes without overwriting saved content unless they explicitly choose to replace it.
9. Handle provider errors, timeouts, rate limits, and oversized context with clear messages.
10. Do not log API keys or entire prompts containing sensitive document content.

Suggested endpoints:
- POST /api/ai/notes
- GET /api/study-assets
- GET /api/study-assets/{asset_id}
- PATCH /api/study-assets/{asset_id}

Keep prompts in reusable functions and separate application logic from provider-specific API calls.
```

**Test:** generate notes from a selected PDF, save them, refresh, and reopen the same notes. Confirm missing credentials produce a clear message, not a crash.

---

## Step 8 — Quick revision sheets and AI tutor

```text
Add revision sheets and document-grounded Q&A.

Revision sheet:
- POST /api/ai/revision-sheet
- Create a compact recap from selected files or saved notes.
- Include key concepts, definitions, comparisons, formulas, and examples only where relevant to the source.
- Save and reopen revision sheets as generated assets.

AI tutor:
- POST /api/ai/ask
- Accept a question plus selected material IDs or chapter context.
- Retrieve relevant chunks before generating the answer.
- Return an answer and source references containing material name and page/slide when available.
- If the selected sources do not support the answer, say that clearly; optionally distinguish any general explanation from source-derived content.
- Verify access permissions before retrieving chunks.
- Include useful empty/error states if extraction or AI is unavailable.

Add UI actions such as "Make quick revision sheet", "Explain simply", and "Ask these documents". Do not make the student copy the whole PDF into a chat box.
```

**Test:** ask a question whose answer is in a source and one whose answer is absent. Verify that the first cites the source and the second does not fabricate a source-based answer.

---

## Step 9 — Quiz generation, taking quizzes, and feedback

```text
Build the quiz workflow.

The student must be able to generate a quiz from:
- One PDF/PPTX/DOCX,
- Multiple selected files,
- A chapter/course,
- Saved AI notes or a revision sheet.

Allow configuration for question count and question type. Support single-select MCQ, multi-select, true/false, and short-answer where reliable. Each question should include answer key and explanation, but do not reveal answers before submission.

Suggested endpoints:
- POST /api/ai/quizzes/generate
- GET /api/quizzes/{quiz_id}
- POST /api/quizzes/{quiz_id}/attempts
- GET /api/quiz-attempts
- GET /api/quiz-attempts/{attempt_id}

Requirements:
1. Ground questions in selected source material.
2. Validate generated question structure before showing the quiz.
3. Clearly handle malformed AI output and offer retry.
4. Grade objective question types server-side; for short answers, if AI grading is used, label it as AI feedback and avoid false certainty.
5. On submission, show score, correct answers, explanations, and suggested topics to revisit.
6. Save attempts, answers, score, source references, and timestamp.
7. Keep each student's quiz history private.
8. Support a quiz from notes as well as directly from the original PDF.
```

**Test:** generate and complete a quiz, verify answer feedback and saved score after refresh, then confirm another student cannot access the attempt.

---

## Step 10 — YouTube lecture recommendations

```text
Implement backend/services/youtube_service.py and the student UI for video recommendations.

Requirements:
1. Identify topics/subtopics from the selected material using extracted text or AI.
2. Use a real YouTube Data API integration or another permitted search integration to retrieve actual results.
3. Read API credentials from backend environment variables only.
4. Show video title, channel, URL, available duration/metadata, and a short relevance reason.
5. Make clear when duration or other metadata is unavailable.
6. Never invent video titles, channels, URLs, view counts, or claims that the system watched a video if it only examined metadata.
7. If the API key is missing, quota is exceeded, or no relevant results are found, show a useful message and setup instructions.
8. Let a student open the video, then manually mark it "Watched" or "Completed". Do not claim that opening a link proves it was watched.

Suggested endpoint:
- POST /api/ai/video-recommendations

Test both the configured and unconfigured states. Do not block the rest of the app when YouTube credentials are missing.
```

---

## Step 11 — Learning activity and progress dashboard

```text
Implement progress tracking based on persisted learning activities and quiz attempts.

Students must be able to mark:
- A document as Not started / In progress / Read (or Completed).
- A video as Not started / Watched.
- A chapter/course as In progress / Completed.
- A revision sheet or flashcard session as completed.

Suggested endpoints:
- PUT /api/learning-activities
- GET /api/progress/summary
- GET /api/progress/courses/{course_id}
- GET /api/progress/topics

Dashboard requirements:
1. Show course/content coverage as completed eligible resources divided by total eligible resources, with the definition visible.
2. Show quiz performance separately, including recent scores and attempt counts.
3. Show revision activity separately.
4. Show topics where the student repeatedly misses quiz questions when topic tagging is available.
5. Never label a student as having mastered a topic solely because a resource is marked complete.
6. Compute metrics from saved records; do not hardcode example percentages.
7. Show an informative empty state for new students.
8. A student's dashboard must not include another student's activity.
9. Use progress bars/charts only when backed by actual stored data.
```

**Test:** mark one resource read, complete a quiz, and finish a revision sheet. Confirm only the corresponding metrics change and persist after refresh.

---

## Step 12 — Student and instructor UI

```text
Build a consistent responsive UI using HTML, Tailwind CSS, and JavaScript. Use a clean academic visual style with clear typography, accessible contrast, and restrained colour.

Student screens:
- Student dashboard: continue studying, courses, personal study space, progress summary, recommended next actions.
- My Courses / Shared Classroom: course cards, chapters, instructor materials.
- My Study Space: folder tree, bulk upload, file list, processing states.
- Material view: preview/metadata where supported, AI notes, quiz, revision sheet, Ask AI, video recommendations, activity status.
- Quiz view: question navigation, answer selection, submit, result and explanations.
- Progress view: coverage, quiz scores, revision activity, recent study history.

Instructor screens:
- Instructor dashboard: owned courses and material management.
- Course editor: create course, chapters/topics, upload files, publish/replace/remove materials.
- Student access/enrollment management appropriate to this MVP.

Requirements:
1. Role-based navigation; do not treat navigation hiding as security.
2. Every button must do its advertised action.
3. Add loading, error, empty, and success states.
4. Confirm before destructive actions.
5. Use responsive layouts for desktop and mobile-sized browser windows.
6. Show clear processing status when files are being extracted.
7. Do not put all features on one crowded screen; use course, folder, and material context.
```

---

## Step 13 — API contract, validation, and Postman

```text
Review the API contract across frontend and backend. Generate a Postman collection named hsblearn-api.postman_collection.json.

Include requests for:
- Registration/login/current user/logout as implemented.
- Course list/create/detail/update.
- Chapter create/list.
- Course material upload/list/detail.
- Personal folder create/list/update/delete.
- Personal bulk upload/list/download.
- AI notes and revision sheet generation.
- AI tutor Q&A.
- Quiz generation, quiz detail, quiz submission, attempt history.
- YouTube recommendations.
- Learning activity updates and progress summaries.

For important routes include success, unauthenticated, forbidden, missing record, invalid input, unsupported file, AI-not-configured, and provider-failure cases where applicable. Add example bodies and expected status codes. Never use real secrets in the collection.

Run the app and test key requests in Postman. Make sure the frontend displays the server's useful error message rather than a generic failure.
```

---

## Step 14 — Security, reliability, and polish pass

```text
Perform a careful review without adding unrelated features.

Check:
1. Every private file, folder, generated note, quiz attempt, and progress route has server-side ownership checks.
2. Every instructor route verifies course ownership/assignment.
3. File type, size, and path handling are safe; filenames cannot traverse directories.
4. API keys are server-side environment variables and .env is ignored by Git.
5. SQL uses parameterised queries.
6. User input and AI output are validated before rendering; avoid injecting untrusted HTML.
7. AI-generated source references point to actual extracted chunks/pages/slides.
8. No fake YouTube results or hardcoded progress metrics exist.
9. Every asynchronous screen has loading, empty, error, and success states.
10. Restarting the server does not lose database records or uploaded files.
11. UI is keyboard-usable, responsive, and has readable contrast.
12. README explains local prototype limitations and production hardening needed.

Fix issues one at a time and report which files changed and how each issue was tested.
```

---

## Step 15 — README and final end-to-end verification

```text
Write a clear README.md containing:
- What HSBLearn is and who it serves.
- The two learning spaces: Shared Classroom and My Study Space.
- MVP features and intentionally deferred features.
- Technology stack and high-level architecture.
- Exact Windows PowerShell setup and run commands.
- Environment variable setup using .env.example (never put real keys in README).
- How to configure AI and YouTube integrations; what works when credentials are missing.
- Database and uploaded-file locations.
- How to open the frontend and FastAPI /docs.
- How to import and run the Postman collection.
- Known limitations, privacy notes, and production deployment work still required.

Then run a clean end-to-end test:
1. Start from a fresh database or a documented test database.
2. Log in as instructor, create a course and chapter, upload materials.
3. Log in as an authorised student and access the shared materials.
4. Upload multiple personal files into My Study Space.
5. Generate and save notes and a quick revision sheet (when AI is configured).
6. Generate and complete a quiz; verify saved results.
7. Request video recommendations (configured or clear unconfigured state).
8. Mark a document read, a video watched, and a chapter completed.
9. Verify the dashboard shows coverage, quiz performance, and revision separately.
10. Try to access another student's private file and confirm access is denied.
11. Restart the server and verify persistence.

List any test that could not be completed and the exact reason. Do not claim a feature works unless it was actually tested.
```

---

## Suggested MVP order

| Priority | Build first |
|---|---|
| P0 | Project setup, database, role/access model, shared courses, private folders, file uploads |
| P1 | Document extraction, AI notes, quick revision sheets, quiz generation and attempts |
| P2 | Learning activity, progress dashboard, document-grounded tutor |
| P3 | YouTube recommendations, smarter next-step suggestions |
| Later | Spaced repetition, adaptive learning, study planner, richer instructor analytics |

## If something breaks

Report what you observe rather than guessing at the cause. For example:

- “The upload request returns 413 and the UI stays on Processing.”
- “Student A can see Student B's folder after changing the folder ID in the URL.”
- “AI notes were saved, but reopening the asset returns a 404.”
- “The quiz score appears in the result screen but is missing after refresh.”
- “The YouTube API key is absent; the page should show setup instructions, not fake videos.”

Check the browser console, the FastAPI terminal, and the failed request/response in the Network tab or Postman. Fix and retest one issue before moving on.
