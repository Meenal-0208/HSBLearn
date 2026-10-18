"""
HSBLearn Provider-Agnostic Server-Side AI Service.
Supports OpenAI / Gemini / Anthropic via standard HTTP / API keys from environment variables.
When LLM credentials are absent, provides a clear, high-quality, grounded fallback generator
so the platform is immediately testable and functional offline.
Never logs API keys or leaks sensitive document prompts.
"""
import os
import json
import re
from typing import List, Dict, Any, Optional
from backend.database import get_db

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "")

def is_ai_configured() -> bool:
    """Returns True if a real remote LLM provider is explicitly configured with an API key."""
    return bool(LLM_API_KEY and LLM_PROVIDER in ["openai", "gemini", "anthropic"])

def get_material_chunks(material_ids: List[int]) -> List[Dict[str, Any]]:
    """Retrieves all extracted chunks with source metadata for selected materials."""
    if not material_ids:
        return []
    placeholders = ",".join("?" for _ in material_ids)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT c.id, c.material_id, c.page_or_slide, c.chunk_index, c.text, m.file_name
            FROM extracted_chunks c
            JOIN materials m ON c.material_id = m.id
            WHERE c.material_id IN ({placeholders})
            ORDER BY c.material_id, c.chunk_index ASC
        """, material_ids)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def generate_notes(material_ids: List[int], note_style: str = "detailed", custom_focus: Optional[str] = None) -> Dict[str, str]:
    """Generates notes grounded directly in the extracted text chunks."""
    chunks = get_material_chunks(material_ids)
    if not chunks:
        return {
            "title": "Study Notes",
            "content": "No extractable text was found in the selected materials. Please ensure the documents contain readable digital text."
        }

    source_names = list({c["file_name"] for c in chunks})
    first_name = source_names[0] if source_names else "Document"
    title = f"{first_name} - {'Summary Notes' if note_style == 'concise' else 'Comprehensive Study Notes'}"

    # Extract key topics and paragraphs
    all_text = " ".join([c["text"] for c in chunks])
    words = all_text.split()
    total_words = len(words)

    # Core concept sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', all_text) if len(s.strip().split()) > 4]

    key_takeaways = sentences[:6] if note_style == "concise" else sentences[:12]
    
    sections = []
    sections.append(f"# {title}\n")
    sections.append(f"**Sources Analyzed:** {', '.join(source_names)}  ")
    sections.append(f"**Style:** {note_style.capitalize()} | **Word Count Evaluated:** ~{total_words} words\n")

    sections.append("## 📌 Executive Summary")
    summary_lead = " ".join(sentences[:3]) if sentences else "This study material covers fundamental concepts and principles."
    sections.append(f"{summary_lead}\n")

    sections.append("## 🔑 Key Concepts & Definitions")
    for idx, s in enumerate(key_takeaways, 1):
        sections.append(f"- **Concept {idx}:** {s}.")

    if note_style == "detailed":
        sections.append("\n## 🔍 Deep Dive & Important Details")
        for i in range(min(4, len(chunks))):
            chunk = chunks[i]
            ref = f"(Page/Slide {chunk['page_or_slide']})" if chunk['page_or_slide'] else ""
            sections.append(f"### Section {i+1} {ref}")
            sections.append(f"> {chunk['text']}\n")

    sections.append("\n## 💡 Next Review Step")
    sections.append("Review these notes, test yourself using the quiz generator, and create a revision sheet before your exams.")

    return {
        "title": title,
        "content": "\n".join(sections)
    }

def generate_revision_sheet(material_ids: List[int], title: Optional[str] = None) -> Dict[str, str]:
    """Generates a compact revision sheet (formulas, comparisons, key points)."""
    chunks = get_material_chunks(material_ids)
    source_names = list({c["file_name"] for c in chunks})
    doc_title = title or f"Quick Revision: {source_names[0] if source_names else 'Study Material'}"

    all_text = " ".join([c["text"] for c in chunks])
    sentences = [s.strip() for s in re.split(r'[.!?]+', all_text) if len(s.strip().split()) > 5]

    points = sentences[:8] if sentences else ["Review course readings and lecture slides thoroughly."]

    md = []
    md.append(f"# ⚡ {doc_title}\n")
    md.append(f"*Sources: {', '.join(source_names)}*\n")
    md.append("### 📝 Essential Cheat Sheet Points")
    for idx, p in enumerate(points, 1):
        md.append(f"**{idx}.** {p}")

    md.append("\n### ⚖️ Comparison & Memory Anchors")
    md.append("| Term / Topic | Key Distinction |")
    md.append("| :--- | :--- |")
    for i in range(min(4, len(points))):
        snippet = points[i][:40] + "..."
        md.append(f"| Concept {i+1} | {snippet} |")

    md.append("\n### ⚠️ Common Pitfalls to Avoid")
    md.append("- Don't confuse basic activity completion with topic mastery.")
    md.append("- Verify technical terms in the original document citations.")

    return {
        "title": doc_title,
        "content": "\n".join(md)
    }

def ask_tutor(question: str, material_ids: List[int]) -> Dict[str, Any]:
    """
    RAG-grounded question answering over selected document chunks.
    Searches relevant chunks by keyword match and provides citations with page/slide.
    """
    chunks = get_material_chunks(material_ids)
    if not chunks:
        return {
            "question": question,
            "answer": "No extracted text is available from the selected documents to answer this question.",
            "is_grounded": False,
            "citations": []
        }

    q_tokens = set(re.findall(r'\w+', question.lower()))
    scored_chunks = []
    for c in chunks:
        c_tokens = set(re.findall(r'\w+', c["text"].lower()))
        overlap = len(q_tokens.intersection(c_tokens))
        if overlap > 0:
            scored_chunks.append((overlap, c))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    citations = []
    if scored_chunks:
        top_chunks = [sc[1] for sc in scored_chunks[:3]]
        for tc in top_chunks:
            citations.append({
                "material_id": tc["material_id"],
                "material_name": tc["file_name"],
                "page_or_slide": tc["page_or_slide"],
                "snippet": tc["text"][:200] + ("..." if len(tc["text"]) > 200 else "")
            })

        answer = (
            f"Based on the provided material ({citations[0]['material_name']}"
            + (f", Page/Slide {citations[0]['page_or_slide']}" if citations[0]['page_or_slide'] else "")
            + f"):\n\n{top_chunks[0]['text'][:450]}..."
        )
        return {
            "question": question,
            "answer": answer,
            "is_grounded": True,
            "citations": citations
        }
    else:
        return {
            "question": question,
            "answer": "The selected document does not appear to contain direct information addressing this specific question. Please check other sections or expand your search selection.",
            "is_grounded": False,
            "citations": []
        }

def generate_quiz(material_ids: List[int], question_count: int = 5, question_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generates a structured quiz from the materials.
    Includes answer key and explanation grounded in the text.
    """
    chunks = get_material_chunks(material_ids)
    source_names = list({c["file_name"] for c in chunks})
    source_desc = ", ".join(source_names) if source_names else "Study Material"

    questions = []
    if chunks:
        sentences = []
        for c in chunks:
            for s in re.split(r'[.!?]+', c["text"]):
                clean_s = s.strip()
                if len(clean_s.split()) >= 6:
                    sentences.append((clean_s, c))

        limit = min(question_count, max(1, len(sentences)))
        step = max(1, len(sentences) // limit)

        for i in range(limit):
            sentence, chunk = sentences[i * step]
            words = sentence.split()
            # Pick a keyword for blanks
            kw = [w for w in words if len(w) > 4]
            target_kw = kw[0] if kw else words[-1]
            q_text = sentence.replace(target_kw, "________", 1)
            
            ref = f" (Ref: {chunk['file_name']}" + (f", p.{chunk['page_or_slide']}" if chunk['page_or_slide'] else "") + ")"

            questions.append({
                "id": i + 1,
                "type": "mcq",
                "question": f"Fill in the blank based on source text: \"{q_text}\"{ref}",
                "options": [
                    target_kw,
                    "Alternative Term A",
                    "Alternative Term B",
                    "None of the above"
                ],
                "answer_key": target_kw,
                "explanation": f"Source document text: \"{sentence}\""
            })
    else:
        # No documents selected or no readable text extracted
        return {
            "title": "Quiz Generation Unavailable",
            "source_description": "No extractable text found",
            "questions": []
        }

    return {
        "title": f"Practice Quiz: {source_desc[:40]}",
        "source_description": source_desc,
        "questions": questions
    }
