// Quiz Client Controller
let quizId = null;
let currentQuiz = null;

document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth('student');
  if (!user) return;

  const urlParams = new URLSearchParams(window.location.search);
  quizId = urlParams.get('id');
  if (!quizId) {
    alert('No quiz ID specified.');
    window.location.href = '/static/student.html';
    return;
  }

  await loadQuizData();
  setupQuizSubmission();
});

async function loadQuizData() {
  try {
    currentQuiz = await apiRequest(`/quizzes/${quizId}`);
    document.getElementById('quizTitle').innerText = currentQuiz.title;
    document.getElementById('quizSource').innerText = `Source Material: ${currentQuiz.source_description}`;

    const container = document.getElementById('questionsContainer');
    container.innerHTML = currentQuiz.questions.map((q, idx) => `
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div class="flex items-center space-x-2">
          <span class="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">${idx + 1}</span>
          <h3 class="text-sm font-bold text-slate-800">${q.question}</h3>
        </div>
        <div class="space-y-2 pl-8">
          ${q.options.map(opt => `
            <label class="flex items-center space-x-3 p-3 rounded-lg border border-slate-200 hover:bg-indigo-50/40 cursor-pointer transition text-sm">
              <input type="radio" name="q_${q.id}" value="${opt}" required class="text-indigo-600 focus:ring-indigo-500">
              <span class="text-slate-700">${opt}</span>
            </label>
          `).join('')}
        </div>
      </div>
    `).join('');
  } catch (err) {
    alert(err.message);
  }
}

function setupQuizSubmission() {
  document.getElementById('quizForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitQuiz');
    btn.disabled = true;
    btn.innerText = 'Submitting & Grading...';

    const answers = [];
    currentQuiz.questions.forEach(q => {
      const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
      answers.push({
        question_id: q.id,
        submitted_answer: selected ? selected.value : null
      });
    });

    try {
      const attempt = await apiRequest(`/quizzes/${quizId}/attempts`, {
        method: 'POST',
        body: JSON.stringify({ answers })
      });

      document.getElementById('quizForm').classList.add('hidden');
      const resContainer = document.getElementById('quizResultContainer');
      resContainer.classList.remove('hidden');

      document.getElementById('resScore').innerText = attempt.score;
      document.getElementById('resTotal').innerText = attempt.total_questions;
      document.getElementById('resPct').innerText = `${attempt.percentage}%`;

      const fbList = document.getElementById('feedbackList');
      fbList.innerHTML = attempt.feedback.map((fb, idx) => `
        <div class="p-4 rounded-xl border ${fb.is_correct ? 'bg-emerald-50/50 border-emerald-200' : 'bg-red-50/50 border-red-200'} space-y-2">
          <div class="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider ${fb.is_correct ? 'text-emerald-700' : 'text-red-700'}">
            <span>${fb.is_correct ? '✓ Correct' : '✗ Incorrect'}</span>
          </div>
          <div class="text-sm font-semibold text-slate-900">${fb.question}</div>
          <div class="text-xs text-slate-600">
            <span>Your Answer: <strong class="${fb.is_correct ? 'text-emerald-800' : 'text-red-800'}">${fb.submitted_answer || 'None'}</strong></span>
            ${!fb.is_correct ? `<span class="ml-3">&middot; Expected: <strong class="text-slate-800">${fb.correct_answer}</strong></span>` : ''}
          </div>
          <div class="text-xs text-slate-500 italic mt-1">
            <strong>Explanation:</strong> ${fb.explanation}
          </div>
        </div>
      `).join('');

    } catch (err) {
      alert(err.message);
      btn.disabled = false;
      btn.innerText = 'Submit Quiz Answers';
    }
  });
}
