// Instructor Dashboard Controller
let cachedInstructorCourses = [];
let selectedCourseIdsToDelete = new Set();
document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth('instructor');
  if (!user) return;

  document.getElementById('instructorName').innerText = user.name;
  await loadInstructorCourses();

  document.getElementById('createCourseForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('courseTitle').value.trim();
    const description = document.getElementById('courseDesc').value.trim();

    try {
      await apiRequest('/courses', {
        method: 'POST',
        body: JSON.stringify({ title, description })
      });
      closeCourseModal();
      document.getElementById('courseTitle').value = '';
      document.getElementById('courseDesc').value = '';
      await loadInstructorCourses();
    } catch (err) {
      alert(err.message);
    }
  });
});

async function loadInstructorCourses() {
  const listEl = document.getElementById('instructorCourses');
  try {
    const courses = await apiRequest('/courses');
    cachedInstructorCourses = courses || [];
    if (!courses || courses.length === 0) {
      listEl.innerHTML = `
        <div class="col-span-full bg-white p-8 rounded-xl border border-dashed border-slate-300 text-center">
          <p class="text-slate-500 font-medium">No courses created yet.</p>
          <button onclick="openCourseModal()" class="mt-3 text-sm text-indigo-600 font-semibold hover:underline">
            + Create your first course
          </button>
        </div>
      `;
      return;
    }

    listEl.innerHTML = courses.map(c => `
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between hover:border-indigo-300 transition">
        <div>
          <div class="flex items-center justify-between text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-2">
            <span>Course #${c.id}</span>
            <span class="px-2 py-0.5 rounded text-xs uppercase ${c.status === 'published' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}">${c.status}</span>
          </div>
          <h3 class="text-lg font-bold text-slate-900">${c.title}</h3>
          <p class="text-slate-600 text-sm mt-2 line-clamp-2">${c.description || 'No description provided.'}</p>
        </div>
        <div class="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
          <span class="text-xs text-slate-500">${c.total_chapters || 0} chapters &middot; ${c.total_materials || 0} files</span>
          <a href="/static/course.html?id=${c.id}" class="text-sm font-semibold text-indigo-600 hover:text-indigo-800">
            Manage Content &rarr;
          </a>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="col-span-full text-red-500 text-sm p-4">${err.message}</div>`;
  }
}

async function deleteCourse(courseId, courseTitle) {
  if (!confirm(`Are you sure you want to delete "${courseTitle}"? All chapters, materials, and quizzes will be deleted permanently.`)) {
    return;
  }
  try {
    await apiRequest(`/courses/${courseId}`, {
      method: 'DELETE'
    });
    await loadInstructorCourses();
  } catch (err) {
    alert(err.message || 'Failed to delete course');
  }
}

function openCourseModal() {
  document.getElementById('courseModal').classList.remove('hidden');
}

function closeCourseModal() {
  document.getElementById('courseModal').classList.add('hidden');
}

function openDeleteCoursesModal() {
  selectedCourseIdsToDelete.clear();
  updateBulkDeleteUI();
  renderDeleteModalList();
  document.getElementById('deleteCoursesModal').classList.remove('hidden');
}

function closeDeleteCoursesModal() {
  document.getElementById('deleteCoursesModal').classList.add('hidden');
}

function renderDeleteModalList() {
  const container = document.getElementById('deleteCoursesList');
  if (!cachedInstructorCourses || cachedInstructorCourses.length === 0) {
    container.innerHTML = `<div class="text-center py-6 text-xs text-slate-400">No courses available to delete.</div>`;
    return;
  }

  container.innerHTML = cachedInstructorCourses.map(c => `
    <label class="flex items-center justify-between p-2.5 hover:bg-slate-50 rounded-lg cursor-pointer transition">
      <div class="flex items-center space-x-3">
        <input type="checkbox" value="${c.id}" onchange="handleCourseSelectionChange(this, ${c.id})" ${selectedCourseIdsToDelete.has(c.id) ? 'checked' : ''} class="w-4 h-4 text-rose-600 rounded border-slate-300 focus:ring-rose-500">
        <div>
          <div class="text-sm font-semibold text-slate-800">${c.title}</div>
          <div class="text-xs text-slate-400">Course #${c.id} &middot; ${c.total_chapters || 0} chapters &middot; ${c.total_materials || 0} files</div>
        </div>
      </div>
      <span class="text-xs text-slate-400 uppercase font-semibold">${c.status}</span>
    </label>
  `).join('');
}

function handleCourseSelectionChange(checkbox, courseId) {
  if (checkbox.checked) {
    selectedCourseIdsToDelete.add(courseId);
  } else {
    selectedCourseIdsToDelete.delete(courseId);
  }
  updateBulkDeleteUI();
}

function toggleSelectAllCourses() {
  if (selectedCourseIdsToDelete.size === cachedInstructorCourses.length) {
    selectedCourseIdsToDelete.clear();
  } else {
    cachedInstructorCourses.forEach(c => selectedCourseIdsToDelete.add(c.id));
  }
  renderDeleteModalList();
  updateBulkDeleteUI();
}

function updateBulkDeleteUI() {
  const count = selectedCourseIdsToDelete.size;
  const countText = document.getElementById('selectedCountText');
  const btn = document.getElementById('btnConfirmBulkDelete');
  const toggleBtn = document.getElementById('btnToggleSelectAll');

  if (countText) countText.innerText = `${count} selected`;
  if (btn) {
    btn.disabled = count === 0;
    btn.innerText = count > 0 ? `Delete (${count}) Selected` : 'Delete Selected';
  }
  if (toggleBtn) {
    toggleBtn.innerText = count === cachedInstructorCourses.length && count > 0 ? 'Deselect All' : 'Select All';
  }
}

async function confirmBulkDeleteCourses() {
  const count = selectedCourseIdsToDelete.size;
  if (count === 0) return;

  if (!confirm(`Are you sure you want to permanently delete ${count} course${count > 1 ? 's' : ''}? All chapters and materials inside them will be completely deleted.`)) {
    return;
  }

  const btn = document.getElementById('btnConfirmBulkDelete');
  btn.disabled = true;
  btn.innerText = 'Deleting...';

  try {
    const ids = Array.from(selectedCourseIdsToDelete);
    for (const id of ids) {
      await apiRequest(`/courses/${id}`, { method: 'DELETE' });
    }
    closeDeleteCoursesModal();
    await loadInstructorCourses();
  } catch (err) {
    alert(err.message || 'Error deleting selected courses');
  } finally {
    btn.disabled = false;
    updateBulkDeleteUI();
  }
}
