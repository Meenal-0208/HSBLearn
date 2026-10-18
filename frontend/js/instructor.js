// Instructor Dashboard Controller
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

function openCourseModal() {
  document.getElementById('courseModal').classList.remove('hidden');
}

function closeCourseModal() {
  document.getElementById('courseModal').classList.add('hidden');
}
