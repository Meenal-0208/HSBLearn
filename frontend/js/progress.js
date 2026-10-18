// Progress Dashboard Client Controller
document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth('student');
  if (!user) return;

  await loadProgressData();
  await loadQuizHistory();
});

async function loadProgressData() {
  try {
    const summary = await apiRequest('/progress/summary');
    if (!summary) return;

    document.getElementById('covPct').innerText = `${summary.content_coverage_pct}%`;
    document.getElementById('covBar').style.width = `${Math.min(100, summary.content_coverage_pct)}%`;

    document.getElementById('quizAvg').innerText = `${summary.average_quiz_score_pct}%`;
    document.getElementById('quizBar').style.width = `${Math.min(100, summary.average_quiz_score_pct)}%`;

    document.getElementById('revCount').innerText = `${summary.revision_sessions_count}`;
    document.getElementById('revBar').style.width = `${Math.min(100, summary.revision_sessions_count * 20)}%`;

    const logEl = document.getElementById('activityLog');
    if (!summary.recent_activities || summary.recent_activities.length === 0) {
      logEl.innerHTML = `<div class="p-6 text-center text-xs text-slate-400">No recorded study activities yet.</div>`;
      return;
    }

    logEl.innerHTML = summary.recent_activities.map(a => `
      <div class="p-4 flex items-center justify-between text-xs">
        <div>
          <span class="font-bold text-slate-800 capitalize">${a.activity_type}</span>
          <span class="text-slate-500 ml-2">Status: <strong>${a.status}</strong></span>
        </div>
        <span class="text-slate-400">${new Date(a.updated_at).toLocaleString()}</span>
      </div>
    `).join('');

  } catch (err) {
    console.error('Error loading progress:', err);
  }
}

async function loadQuizHistory() {
  const listEl = document.getElementById('quizHistoryList');
  try {
    const attempts = await apiRequest('/quiz-attempts');
    if (!attempts || attempts.length === 0) {
      listEl.innerHTML = `<div class="p-6 text-center text-xs text-slate-400">No quizzes taken yet.</div>`;
      return;
    }

    listEl.innerHTML = attempts.map(att => `
      <div class="p-4 flex items-center justify-between">
        <div>
          <h4 class="font-bold text-slate-900 text-sm">${att.quiz_title || 'Practice Quiz'}</h4>
          <p class="text-xs text-slate-500 mt-0.5">Attempted on: ${new Date(att.submitted_at).toLocaleDateString()}</p>
        </div>
        <div class="text-right">
          <div class="text-sm font-extrabold ${att.percentage >= 70 ? 'text-emerald-600' : 'text-slate-700'}">
            ${att.score} / ${att.total_questions} (${att.percentage}%)
          </div>
          <span class="text-[11px] text-slate-400">Recorded Attempt</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="p-4 text-xs text-red-500">${err.message}</div>`;
  }
}
