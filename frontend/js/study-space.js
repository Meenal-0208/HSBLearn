// My Study Space Client Controller
let activeFolderId = null;
let allFolders = [];

document.addEventListener('DOMContentLoaded', async () => {
  const user = checkAuth('student');
  if (!user) return;

  await loadFolders();
  await loadPersonalMaterials();
  setupStudySpaceForms();
});

async function loadFolders() {
  const listEl = document.getElementById('foldersList');
  const destSelect = document.getElementById('destFolderSelect');
  try {
    allFolders = await apiRequest('/study-space/folders');
    destSelect.innerHTML = `<option value="">Root / General</option>` + allFolders.map(f => `
      <option value="${f.id}">${f.name}</option>
    `).join('');

    if (!allFolders || allFolders.length === 0) {
      listEl.innerHTML = `<div class="p-4 text-xs text-slate-400">No folders created yet.</div>`;
      return;
    }

    listEl.innerHTML = allFolders.map(f => `
      <div onclick="filterByFolder(${f.id}, '${f.name}')" class="p-3 flex justify-between items-center hover:bg-slate-50 cursor-pointer text-sm ${activeFolderId === f.id ? 'bg-indigo-50 font-semibold text-indigo-700' : 'text-slate-700'}">
        <div class="flex items-center space-x-2">
          <span>📁</span>
          <span>${f.name}</span>
        </div>
        <button onclick="event.stopPropagation(); deleteFolder(${f.id})" class="text-xs text-slate-400 hover:text-red-500">
          &times;
        </button>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="p-4 text-xs text-red-500">${err.message}</div>`;
  }
}

async function loadPersonalMaterials(folderId = null) {
  const listEl = document.getElementById('personalFilesList');
  try {
    const endpoint = folderId ? `/study-space/materials?folder_id=${folderId}` : '/study-space/materials';
    const materials = await apiRequest(endpoint);

    document.getElementById('fileCountBadge').innerText = `${materials.length} files`;

    if (!materials || materials.length === 0) {
      listEl.innerHTML = `
        <div class="p-8 bg-white border border-slate-200 rounded-xl text-center text-sm text-slate-400">
          No files uploaded in this folder. Click "+ Bulk Upload Files" to add PDFs, DOCXs, or PPTXs.
        </div>
      `;
      return;
    }

    listEl.innerHTML = materials.map(m => `
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
          <button onclick="deleteMat(${m.id})" class="text-xs text-red-600 hover:bg-red-50 px-2 py-1.5 rounded-lg">
            Delete
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="p-4 text-xs text-red-500">${err.message}</div>`;
  }
}

function filterByFolder(folderId, name = null) {
  activeFolderId = folderId;
  document.getElementById('currentViewTitle').innerText = name ? `Folder: ${name}` : 'All Private Materials';
  loadFolders();
  loadPersonalMaterials(folderId);
}

function setupStudySpaceForms() {
  document.getElementById('folderForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('folderName').value.trim();
    try {
      await apiRequest('/study-space/folders', {
        method: 'POST',
        body: JSON.stringify({ name })
      });
      closeFolderModal();
      document.getElementById('folderName').value = '';
      await loadFolders();
    } catch (err) {
      alert(err.message);
    }
  });

  document.getElementById('personalUploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('studyFiles');
    if (!fileInput.files.length) return;

    const formData = new FormData();
    const folderId = document.getElementById('destFolderSelect').value;
    if (folderId) formData.append('personal_folder_id', folderId);

    for (let i = 0; i < fileInput.files.length; i++) {
      formData.append('files', fileInput.files[i]);
    }

    document.getElementById('uploadProgress').classList.remove('hidden');
    document.getElementById('btnPersonalUpload').disabled = true;

    try {
      await apiRequest('/study-space/materials', {
        method: 'POST',
        body: formData,
        isFormData: true
      });
      closeUploadModal();
      fileInput.value = '';
      await loadPersonalMaterials(activeFolderId);
    } catch (err) {
      alert(err.message);
    } finally {
      document.getElementById('uploadProgress').classList.add('hidden');
      document.getElementById('btnPersonalUpload').disabled = false;
    }
  });
}

async function deleteFolder(folderId) {
  if (!confirm('Delete this folder and move contained materials to root?')) return;
  try {
    await apiRequest(`/study-space/folders/${folderId}`, { method: 'DELETE' });
    if (activeFolderId === folderId) activeFolderId = null;
    await loadFolders();
    await loadPersonalMaterials(activeFolderId);
  } catch (err) {
    alert(err.message);
  }
}

async function deleteMat(matId) {
  if (!confirm('Permanently delete this private material?')) return;
  try {
    await apiRequest(`/materials/${matId}`, { method: 'DELETE' });
    await loadPersonalMaterials(activeFolderId);
  } catch (err) {
    alert(err.message);
  }
}

function openFolderModal() { document.getElementById('folderModal').classList.remove('hidden'); }
function closeFolderModal() { document.getElementById('folderModal').classList.add('hidden'); }
function openUploadModal() { document.getElementById('uploadModal').classList.remove('hidden'); }
function closeUploadModal() { document.getElementById('uploadModal').classList.add('hidden'); }
