// Material Study & AI Client Controller
let materialId = null;
let currentMaterial = null;

document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth();
  if (!user) return;

  const urlParams = new URLSearchParams(window.location.search);
  materialId = urlParams.get('id');
  if (!materialId) {
    alert('No material ID specified.');
    window.location.href = user.role === 'instructor' ? '/static/instructor.html' : '/static/student.html';
    return;
  }

  await loadMaterialData();
});

async function loadMaterialData() {
  try {
    currentMaterial = await apiRequest(`/materials/${materialId}`);
    document.getElementById('matFileName').innerText = currentMaterial.file_name;
    document.getElementById('matVisibility').innerText = currentMaterial.visibility === 'course' ? 'Shared Course Document' : 'Personal Study Document';
    document.getElementById('matExtractionStatus').innerText = currentMaterial.extraction_status;
    document.getElementById('matMetaDetails').innerText = `${Math.round(currentMaterial.file_size / 1024)} KB &middot; ${currentMaterial.chunks_count || 0} extracted passages ready for AI`;
    document.getElementById('btnDownloadMat').href = `/api/materials/${materialId}/download`;
  } catch (err) {
    alert(err.message);
  }
}

function switchTab(tab) {
  ['notes', 'revision', 'ask', 'quiz', 'videos'].forEach(t => {
    document.getElementById(`tab-${t}`).className = 'px-6 py-3.5 text-sm font-semibold border-b-2 border-transparent text-slate-500 hover:text-slate-800';
    document.getElementById(`panel-${t}`).classList.add('hidden');
  });
  document.getElementById(`tab-${tab}`).className = 'px-6 py-3.5 text-sm font-semibold border-b-2 border-indigo-600 text-indigo-600';
  document.getElementById(`panel-${tab}`).classList.remove('hidden');
}

async function onStatusChanged() {
  const status = document.getElementById('activityStatusSelect').value;
  try {
    await apiRequest('/learning-activities', {
      method: 'PUT',
      body: JSON.stringify({
        activity_type: 'read',
        status: status,
        material_id: parseInt(materialId)
      })
    });
  } catch (err) {
    console.error('Failed to update activity status:', err);
  }
}

async function triggerGenerateNotes() {
  const btn = document.getElementById('btnGenNotes');
  const output = document.getElementById('notesOutput');
  const noteStyle = document.querySelector('input[name="noteStyle"]:checked').value;

  btn.disabled = true;
  btn.innerText = 'Analyzing & Generating...';
  output.innerText = 'Processing document chunks and extracting core principles...';

  try {
    const res = await apiRequest('/ai/notes', {
      method: 'POST',
      body: JSON.stringify({
        material_ids: [parseInt(materialId)],
        note_style: noteStyle
      })
    });
    output.innerText = res.content;
  } catch (err) {
    output.innerText = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = 'Generate Grounded Notes';
  }
}

async function triggerGenerateRevision() {
  const btn = document.getElementById('btnGenRevision');
  const output = document.getElementById('revisionOutput');

  btn.disabled = true;
  btn.innerText = 'Synthesizing...';
  output.innerText = 'Extracting cheat-sheet definitions and comparison pairs...';

  try {
    const res = await apiRequest('/ai/revision-sheet', {
      method: 'POST',
      body: JSON.stringify({
        material_ids: [parseInt(materialId)]
      })
    });
    output.innerText = res.content;
  } catch (err) {
    output.innerText = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = 'Generate Revision Sheet';
  }
}

async function askTutorQuestion() {
  const q = document.getElementById('tutorQuery').value.trim();
  if (!q) return;

  const btn = document.getElementById('btnAskTutor');
  const ansContainer = document.getElementById('tutorAnswerContainer');
  const ansText = document.getElementById('tutorAnswerText');
  const citList = document.getElementById('citationsList');

  btn.disabled = true;
  btn.innerText = 'Searching...';

  try {
    const res = await apiRequest('/ai/ask', {
      method: 'POST',
      body: JSON.stringify({
        question: q,
        material_ids: [parseInt(materialId)]
      })
    });

    ansContainer.classList.remove('hidden');
    ansText.innerText = res.answer;

    if (res.citations && res.citations.length > 0) {
      citList.innerHTML = res.citations.map(c => `
        <div class="p-3 bg-white border border-slate-200 rounded-lg text-xs">
          <div class="font-bold text-slate-800">📄 ${c.material_name} ${c.page_or_slide ? `(Page/Slide ${c.page_or_slide})` : ''}</div>
          <div class="text-slate-600 italic mt-1">"${c.snippet}"</div>
        </div>
      `).join('');
    } else {
      citList.innerHTML = `<div class="text-xs text-slate-400">No specific citations found for this query.</div>`;
    }
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Ask AI';
  }
}

async function generateMaterialQuiz() {
  try {
    const res = await apiRequest('/ai/quizzes/generate', {
      method: 'POST',
      body: JSON.stringify({
        material_ids: [parseInt(materialId)],
        question_count: 5,
        question_types: ['mcq']
      })
    });
    window.location.href = `/static/quiz.html?id=${res.id}`;
  } catch (err) {
    alert(err.message);
  }
}

async function loadVideoRecommendations() {
  const btn = document.getElementById('btnFetchVideos');
  const list = document.getElementById('videosList');

  btn.disabled = true;
  btn.innerText = 'Searching...';

  try {
    const res = await apiRequest('/ai/video-recommendations', {
      method: 'POST',
      body: JSON.stringify({
        material_ids: [parseInt(materialId)],
        note_style: 'concise'
      })
    });

    if (!res.configured) {
      list.innerHTML = `
        <div class="bg-amber-50 border border-amber-200 rounded-xl p-5 text-sm text-amber-800">
          <div class="font-bold mb-1">⚠️ YouTube API Key Not Configured</div>
          <div>${res.message}</div>
        </div>
      `;
      return;
    }

    if (!res.recommendations || res.recommendations.length === 0) {
      list.innerHTML = `<div class="p-8 text-center text-sm text-slate-400">No matching YouTube lectures found.</div>`;
      return;
    }

    list.innerHTML = res.recommendations.map(v => `
      <div class="bg-white p-4 border border-slate-200 rounded-xl flex justify-between items-center">
        <div>
          <h4 class="font-bold text-slate-900 text-sm">${v.title}</h4>
          <p class="text-xs text-slate-500 mt-0.5">Channel: ${v.channel} &middot; Topic: ${v.source_topic}</p>
          <p class="text-xs text-indigo-600 mt-1">${v.relevance_reason}</p>
        </div>
        <a href="${v.url}" target="_blank" class="text-xs bg-red-50 text-red-700 hover:bg-red-100 font-semibold px-3 py-1.5 rounded-lg transition whitespace-nowrap">
          Watch on YouTube &rarr;
        </a>
      </div>
    `).join('');
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Search YouTube';
  }
}
