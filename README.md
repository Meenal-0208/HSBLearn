# HSBLearn — AI-Native Learning Management & Personal Study Platform

**Version:** 1.0.0 (MVP)  
**Architecture:** Python + FastAPI · SQLite · Vanilla HTML5 + Tailwind CSS + JavaScript · Postman

---

## 1. What HSBLearn Is and Who It Serves

HSBLearn bridges institutional college learning and personal independent study into a unified, secure platform. It serves two distinct roles:

- **👨‍🏫 Instructors:** Create courses, organize modules into chapters/topics, upload course materials (PDF, DOCX, PPTX, TXT), and manage course access for enrolled students.
- **🎓 Students:** Access shared classroom materials and manage a completely private **My Study Space** with custom nested folders. Turn study materials into:
  - **Document-Grounded AI Study Notes** (Detailed or Concise)
  - **Quick Revision Sheets** (Definitions, comparison tables, and memory anchors)
  - **Grounded AI Tutor Q&A** with exact document citations, slide, and page numbers
  - **Interactive Practice Quizzes** with server-side objective grading and explanatory feedback
  - **Real YouTube Lecture Recommendations** matching key extracted topics
  - **Learning Progress & Analytics** separating content coverage, quiz performance, and revision activity.

---

## 2. The Two Learning Spaces

1. **Shared Classroom:** Instructor-curated courses and materials. Only enrolled students and the assigned instructor can access these materials.
2. **My Study Space:** A student's private personal workspace. Personal folders and uploaded materials are isolated and strictly forbidden to all other users.

---

## 3. Technology Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic, python-jose (JWT), python-multipart
- **Document Extractors:** `pypdf`, `python-docx`, `python-pptx`
- **Database:** SQLite (`data/hsblearn.db`) with foreign key constraints, indexes, and transactional connection pooling
- **Storage:** Local isolated uploads folder (`uploads/`) with UUID-sanitized storage paths
- **Frontend:** Vanilla HTML5, Tailwind CSS (via CDN), ES6 Vanilla JavaScript (zero node build step required)
- **AI Layer:** Provider-agnostic server-side LLM adapter supporting OpenAI, Google Gemini, Anthropic, or high-fidelity offline fallback generator

---

## 4. Setup and Run on Windows PowerShell

### Step 1: Create & Activate Virtual Environment
```powershell
# Open Windows PowerShell in the project directory:
cd "c:\Users\Meenal Kothari\OneDrive\Desktop\HSBLearn"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables (Optional)
```powershell
Copy-Item .env.example .env
```
*Note: The platform functions completely out-of-the-box in local prototype mode even without remote AI keys.*

### Step 4: Run the FastAPI Server
```powershell
uvicorn backend.main:app --reload --port 9000
```

---

## 5. Exploring the Platform

Once the server is running, navigate to:

- **Web Application:** [http://127.0.0.1:9000](http://127.0.0.1:9000)
- **Interactive Swagger Docs:** [http://127.0.0.1:9000/docs](http://127.0.0.1:9000/docs)
- **Postman API Collection:** `hsblearn-api.postman_collection.json`

### Seeded Demo Accounts:
| Role | Email | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Instructor** | `instructor@hsblearn.local` | `instructor123` | Manage CS 101 course, upload lecture slides, enroll students |
| **Student 1** | `student@hsblearn.local` | `student123` | Maya Lin — Enrolled in CS 101, has personal study folders |
| **Student 2** | `student2@hsblearn.local` | `student123` | James Reed — Demonstrates access boundaries and permission isolation |

---

## 6. Security & Privacy Guarantees

1. **Server-Side Role & Ownership Checks:** Hiding buttons on the client is never treated as security. Every course, folder, file download, quiz attempt, and AI request verifies user permissions on the server.
2. **Private File Isolation:** A student attempting to access or delete another student's personal folder or document receives an immediate `403 Forbidden`.
3. **No Fabricated Outputs:** YouTube recommendations return clear setup guidance when API credentials are absent, rather than inventing fake video URLs or channels.
4. **Distinction Between Activity & Mastery:** Content coverage (e.g. marking a PDF read) is tracked separately from demonstrated quiz scores and active revision.

---

## 7. Running Automated End-to-End Tests

```powershell
python -m unittest tests/test_e2e.py
```
Validates:
- Health checks and JWT authentication
- Cross-student study space isolation (403 verification)
- Instructor course creation role gating (403 verification)
- Multi-format file upload and text chunking
- AI study notes, revision sheets, and grounded Q&A citations
- Quiz generation, taking, server-side grading, and progress metric calculations.
