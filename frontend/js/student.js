// Student Dashboard Controller
document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth('student');
  if (!user) return;

  document.getElementById('userName').innerText = user.name;
  document.getElementById('welcomeName').innerText = user.name.split(' ')[0];

  await loadProgressSummary();
  await loadEnrolledCourses();
  await loadStudyAssets();
});

async function loadProgressSummary() {
  try {
    const summary = await apiRequest('/progress/summary');
    if (!summary) return;
    document.getElementById('statCoverage').innerText = `${summary.content_coverage_pct}%`;
    document.getElementById('statQuiz').innerText = `${summary.average_quiz_score_pct}%`;
    document.getElementById('statQuizCount').innerText = `${summary.total_quizzes_taken} attempts recorded`;
    document.getElementById('statRevision').innerText = `${summary.revision_sessions_count}`;
  } catch (err) {
    console.error('Error loading progress summary:', err);
  }
}

async function loadEnrolledCourses() {
  const listEl = document.getElementById('coursesList');
  try {
    const courses = await apiRequest('/courses');
    if (!courses || courses.length === 0) {
      listEl.innerHTML = `
        <div class="col-span-full bg-white p-8 rounded-xl border border-dashed border-slate-300 text-center">
          <p class="text-slate-500 font-medium">No courses assigned yet.</p>
          <p class="text-xs text-slate-400 mt-1">Ask your instructor to grant access or explore your private My Study Space.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = courses.map(c => `
      <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 flex flex-col justify-between hover:border-indigo-400 dark:hover:border-indigo-600 transition">
        <div>
          <div class="flex items-center justify-between text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mb-2">
            <span>Course</span>
            <span class="text-slate-400 font-normal">Instructor: ${c.instructor_name || 'Assigned'}</span>
          </div>
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">${c.title}</h3>
          <p class="text-slate-600 dark:text-slate-400 text-sm mt-2 line-clamp-2">${c.description || 'No description provided.'}</p>
        </div>
        <div class="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <span class="text-xs text-slate-500 dark:text-slate-400">${c.total_chapters || 0} chapters &middot; ${c.total_materials || 0} files</span>
          <a href="/static/course.html?id=${c.id}" class="text-sm font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800">
            Open Course &rarr;
          </a>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="col-span-full text-red-500 text-sm p-4">${err.message}</div>`;
  }
}

async function loadStudyAssets() {
  const listEl = document.getElementById('assetsList');
  try {
    const assets = await apiRequest('/study-assets');
    if (!assets || assets.length === 0) {
      listEl.innerHTML = `
        <div class="col-span-full bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 text-center">
          <p class="text-sm text-slate-500 dark:text-slate-400">No generated study notes or revision sheets yet.</p>
          <p class="text-xs text-slate-400 mt-1">Open any course or personal material to generate notes with AI.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = assets.map(a => `
      <div class="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm flex justify-between items-start">
        <div>
          <span class="text-xs uppercase font-semibold px-2.5 py-0.5 rounded-full ${a.asset_type === 'notes' ? 'bg-blue-100 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300' : 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300'}">
            ${a.asset_type === 'notes' ? 'Study Notes' : 'Revision Sheet'}
          </span>
          <h4 class="font-bold text-slate-900 dark:text-white mt-2">${a.title}</h4>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Created: ${new Date(a.created_at).toLocaleDateString()}</p>
        </div>
        <button onclick="viewAsset(${a.id})" class="text-xs bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-3 py-1.5 rounded-xl font-medium transition">
          View
        </button>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="col-span-full text-red-500 text-sm p-4">${err.message}</div>`;
  }
}

async function viewAsset(assetId) {
  try {
    const asset = await apiRequest(`/study-assets/${assetId}`);
    if (asset) {
      alert(`=== ${asset.title} ===\n\n${asset.content}`);
    }
  } catch (err) {
    alert(err.message);
  }
}
