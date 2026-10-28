// Course Details & Content Controller
let courseId = null;
let currentRole = null;
let cachedChapters = [];

document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth();
  if (!user) return;
  currentRole = user.role;

  const urlParams = new URLSearchParams(window.location.search);
  courseId = urlParams.get('id');
  if (!courseId) {
    alert('No course ID specified.');
    window.location.href = currentRole === 'instructor' ? '/static/instructor.html' : '/static/student.html';
    return;
  }

  document.getElementById('backHomeLink').href = currentRole === 'instructor' ? '/static/instructor.html' : '/static/student.html';

  if (currentRole === 'instructor') {
    document.getElementById('instructorActions').classList.remove('hidden');
  }

  await loadCourseData();
  setupForms();
});

async function loadCourseData() {
  try {
    const course = await apiRequest(`/courses/${courseId}`);
    document.getElementById('courseTitle').innerText = course.title;
    document.getElementById('courseDesc').innerText = course.description || 'Shared instructor materials and curriculum.';

    // Load chapters
    cachedChapters = await apiRequest(`/courses/${courseId}/chapters`);
    const chapList = document.getElementById('chaptersList');
    const chapSelect = document.getElementById('chapSelect');

    if (!cachedChapters || cachedChapters.length === 0) {
      chapList.innerHTML = `<div class="p-4 text-xs text-slate-400">No chapters added yet.</div>`;
    } else {
      chapList.innerHTML = cachedChapters.map((c, idx) => `
        <div class="p-4 hover:bg-slate-50 transition cursor-pointer">
          <div class="text-xs font-semibold text-indigo-600 uppercase">Module ${idx + 1}</div>
          <div class="font-bold text-slate-900 text-sm mt-0.5">${c.title}</div>
          <div class="text-xs text-slate-500 mt-1">${c.description || ''}</div>
        </div>
      `).join('');

      chapSelect.innerHTML = `<option value="">General (No chapter)</option>` + cachedChapters.map(c => `
        <option value="${c.id}">${c.title}</option>
      `).join('');
    }

    // Load materials
    const materials = await apiRequest(`/courses/${courseId}/materials`);
    const matList = document.getElementById('materialsList');
    document.getElementById('materialsCount').innerText = `${materials.length} files`;

    if (!materials || materials.length === 0) {
      matList.innerHTML = `
        <div class="p-8 bg-white border border-slate-200 rounded-xl text-center text-sm text-slate-400">
          No learning materials uploaded to this course yet.
        </div>
      `;
      return;
    }

    matList.innerHTML = materials.map(m => `
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between hover:border-slate-300 transition">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-xs uppercase">
            ${m.file_type.replace('.', '')}
          </div>
          <div>
            <h4 class="font-bold text-slate-900 text-sm">${m.file_name}</h4>
            <div class="flex items-center space-x-2 text-xs text-slate-400 mt-0.5">
              <span>${Math.round(m.file_size / 1024)} KB</span>
              <span>&middot;</span>
              <span class="capitalize text-slate-600">${m.extraction_status === 'ready' ? `${m.chunks_count || 'Text'} chunks extracted` : m.extraction_status}</span>
            </div>
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <a href="/static/material.html?id=${m.id}" class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold px-3 py-1.5 rounded-lg transition">
            Study / AI Tools &rarr;
          </a>
          <a href="/api/materials/${m.id}/download" download class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg transition">
            Download
          </a>
          ${currentRole === 'instructor' ? `
            <button onclick="deleteMat(${m.id})" class="text-xs text-red-600 hover:bg-red-50 px-2 py-1.5 rounded-lg">
              Delete
            </button>
          ` : ''}
        </div>
      </div>
    `).join('');

  } catch (err) {
    alert(err.message);
  }
}

function setupForms() {
  document.getElementById('chapterForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('chapTitle').value.trim();
    const description = document.getElementById('chapDesc').value.trim();

    try {
      await apiRequest(`/courses/${courseId}/chapters`, {
        method: 'POST',
        body: JSON.stringify({ title, description, order_index: cachedChapters.length + 1 })
      });
      closeChapterModal();
      document.getElementById('chapTitle').value = '';
      document.getElementById('chapDesc').value = '';
      await loadCourseData();
    } catch (err) {
      alert(err.message);
    }
  });

  document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('courseFiles');
    if (!fileInput.files.length) return;

    const formData = new FormData();
    const chapId = document.getElementById('chapSelect').value;
    if (chapId) formData.append('chapter_id', chapId);

    for (let i = 0; i < fileInput.files.length; i++) {
      formData.append('files', fileInput.files[i]);
    }

    document.getElementById('uploadStatusText').classList.remove('hidden');
    document.getElementById('btnUploadSubmit').disabled = true;

    try {
      await apiRequest(`/courses/${courseId}/materials`, {
        method: 'POST',
        body: formData,
        isFormData: true
      });
      closeUploadModal();
      fileInput.value = '';
      await loadCourseData();
    } catch (err) {
      alert(err.message);
    } finally {
      document.getElementById('uploadStatusText').classList.add('hidden');
      document.getElementById('btnUploadSubmit').disabled = false;
    }
  });

  document.getElementById('enrollForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('enrollEmail').value.trim();
    try {
      const res = await apiRequest(`/courses/${courseId}/access`, {
        method: 'POST',
        body: JSON.stringify({ student_email: email })
      });
      alert(res.message);
      closeEnrollModal();
      document.getElementById('enrollEmail').value = '';
    } catch (err) {
      alert(err.message);
    }
  });
}

async function deleteMat(matId) {
  if (!confirm('Are you sure you want to remove this course material?')) return;
  try {
    await apiRequest(`/materials/${matId}`, { method: 'DELETE' });
    await loadCourseData();
  } catch (err) {
    alert(err.message);
  }
}

async function handleDeleteCurrentCourse() {
  const title = document.getElementById('courseTitle').innerText || 'this course';
  if (!confirm(`Are you sure you want to permanently delete "${title}"? All chapters and materials will be deleted.`)) {
    return;
  }
  try {
    await apiRequest(`/courses/${courseId}`, { method: 'DELETE' });
    window.location.href = '/static/instructor.html';
  } catch (err) {
    alert(err.message || 'Failed to delete course');
  }
}

function openChapterModal() { document.getElementById('chapterModal').classList.remove('hidden'); }
function closeChapterModal() { document.getElementById('chapterModal').classList.add('hidden'); }
function openUploadModal() { document.getElementById('uploadModal').classList.remove('hidden'); }
function closeUploadModal() { document.getElementById('uploadModal').classList.add('hidden'); }
function openEnrollModal() { document.getElementById('enrollModal').classList.remove('hidden'); }
function closeEnrollModal() { document.getElementById('enrollModal').classList.add('hidden'); }
