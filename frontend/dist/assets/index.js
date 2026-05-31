const API = 'https://python-portfolio-y0z8.onrender.com';

function $(id){return document.getElementById(id)}

/* ─── App shell ─── */
const app = $('app');
app.innerHTML = `
<header>
  <h1>Portfolio API</h1>
  <a href="https://voicenotesite.github.io/WebBartosz/" target="_blank">WebBartosz</a>
  <span class="env">python-portfolio-y0z8</span>
</header>
<div class="tabs" id="tabs">
  <div class="tab active" data-tab="chat">💬 Chat</div>
  <div class="tab" data-tab="queue">📋 Queue <span class="badge" id="queueCount">0</span></div>
  <div class="tab" data-tab="rag">📄 RAG Q&A</div>
</div>
<main>
  <div class="panel active" id="panel-chat">
    <h2>💬 AI Chat</h2>
    <p class="sub">Send a message to GPT-3.5 or GPT-4</p>
    <div class="chat-box" id="chatBox"></div>
    <div class="row">
      <select id="chatModel"><option value="gpt-3.5-turbo">GPT-3.5 Turbo</option><option value="gpt-4">GPT-4</option></select>
      <button class="btn secondary sm" id="chatClear">Clear</button>
    </div>
    <div class="row">
      <input id="chatInput" placeholder="Type a message..." autocomplete="off">
      <button class="btn primary" id="chatSend">Send</button>
    </div>
  </div>
  <div class="panel" id="panel-queue">
    <h2>📋 Task Queue</h2>
    <p class="sub">Create and monitor background tasks with real-time progress</p>
    <div class="row">
      <input id="taskName" placeholder="Task name">
      <select id="taskType">
        <option value="email">Email Campaign</option>
        <option value="report">Generowanie Raportu</option>
        <option value="export">Eksport Danych</option>
        <option value="generic">Generic</option>
      </select>
      <button class="btn primary" id="taskCreate">Create</button>
      <button class="btn danger" id="taskClear">Clear all</button>
    </div>
    <div id="taskList"></div>
  </div>
  <div class="panel" id="panel-rag">
    <h2>📄 RAG PDF Q&A</h2>
    <p class="sub">Upload a PDF and ask questions about its content</p>
    <div class="upload-area" id="uploadArea">
      <div class="icon">📤</div>
      <p>Drop a PDF here or click to upload</p>
    </div>
    <input type="file" id="fileInput" accept=".pdf" style="display:none">
    <div class="doc-list" id="docList"></div>
    <div class="query-area">
      <input id="ragInput" placeholder="Ask a question about the PDF..." autocomplete="off" disabled>
      <button class="btn primary" id="ragAsk" disabled>Ask</button>
    </div>
    <div class="answer-box" id="answerBox" style="display:none"></div>
  </div>
</main>`;

/* ─── Tab switching ─── */
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    $(`panel-${tab.dataset.tab}`).classList.add('active');
    if (tab.dataset.tab === 'queue') fetchTasks();
    if (tab.dataset.tab === 'rag') fetchDocs();
  });
});

/* ─── Chat ─── */
const chatBox = $('chatBox');
const chatInput = $('chatInput');
$('chatSend').addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage() });
$('chatClear').addEventListener('click', () => { chatBox.innerHTML = '' });

async function sendMessage() {
  const msg = chatInput.value.trim();
  if (!msg) return;
  chatInput.value = '';
  appendMsg(msg, 'user');
  const sendBtn = $('chatSend');
  sendBtn.disabled = true; sendBtn.innerHTML = '<span class="spinner"></span>';
  try {
    const res = await fetch(`${API}/api/chat/message`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, model: $('chatModel').value })
    });
    const data = await res.json();
    appendMsg(data.response || JSON.stringify(data), 'assistant');
  } catch (e) {
    appendMsg('Error: ' + e.message, 'assistant');
  }
  sendBtn.disabled = false; sendBtn.textContent = 'Send';
}

function appendMsg(text, role) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = role === 'user' ? text : `<div class="sender">${$('chatModel').value}</div>` + text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

/* ─── Queue ─── */
const taskList = $('taskList');
let wsConnections = {};
$('taskCreate').addEventListener('click', createTask);
$('taskClear').addEventListener('click', clearTasks);

async function fetchTasks() {
  try {
    const res = await fetch(`${API}/api/queue/tasks`);
    const tasks = await res.json();
    renderTasks(tasks);
  } catch (e) { taskList.innerHTML = '<div class="card" style="color:var(--red)">Failed to load tasks</div>' }
}

function renderTasks(tasks) {
  if (!tasks.length) { taskList.innerHTML = '<div class="card" style="color:var(--text2);text-align:center;padding:30px">No tasks yet</div>'; $('queueCount').textContent = '0'; return }
  $('queueCount').textContent = tasks.length;
  taskList.innerHTML = '';
  tasks.forEach(t => taskList.appendChild(taskCard(t)));
  tasks.forEach(t => { if (t.status === 'pending' || t.status === 'processing') connectWS(t.id) });
}

function taskCard(t) {
  const card = document.createElement('div');
  card.className = 'card';
  card.id = `task-${t.id}`;
  card.innerHTML = `
    <div class="h">
      <h4>${t.name}</h4>
      <span class="status ${t.status}">${t.status}</span>
    </div>
    <div class="meta">
      <span>${t.task_type}</span>
      <span>${new Date(t.created_at).toLocaleTimeString()}</span>
      <span>progress: ${t.progress}%</span>
      ${t.status === 'pending' || t.status === 'processing' ? `<button class="btn danger sm" onclick="cancelTask('${t.id}')">Cancel</button>` : ''}
    </div>
    <div class="progress"><div class="bar" style="width:${t.progress}%"></div></div>
    ${t.result ? `<div class="result"><div class="label">Result</div>${t.result}</div>` : ''}
    ${t.error ? `<div class="result" style="color:var(--red)"><div class="label">Error</div>${t.error}</div>` : ''}`;
  return card;
}

async function createTask() {
  const name = $('taskName').value.trim() || 'Task ' + Date.now();
  const type = $('taskType').value;
  try {
    await fetch(`${API}/api/queue/tasks`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, task_type: type })
    });
    $('taskName').value = '';
    fetchTasks();
  } catch (e) { alert('Failed to create task') }
}

async function cancelTask(id) {
  try {
    await fetch(`${API}/api/queue/tasks/${id}/cancel`, { method: 'POST' });
    fetchTasks();
  } catch (e) {}
}

async function clearTasks() {
  try {
    await fetch(`${API}/api/queue/tasks`, { method: 'DELETE' });
    fetchTasks();
  } catch (e) {}
}

function connectWS(id) {
  if (wsConnections[id]) return;
  const ws = new WebSocket(`wss://python-portfolio-y0z8.onrender.com/api/queue/ws/${id}`);
  wsConnections[id] = ws;
  ws.onmessage = e => {
    const t = JSON.parse(e.data);
    const card = document.getElementById(`task-${t.id}`);
    if (card) card.outerHTML = taskCard(t).outerHTML;
  };
  ws.onclose = () => { delete wsConnections[id]; if (document.getElementById(`task-${id}`)) fetchTasks() };
}

/* ─── RAG ─── */
const uploadArea = $('uploadArea');
const fileInput = $('fileInput');
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.style.borderColor = 'var(--accent)' });
uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = '' });
uploadArea.addEventListener('drop', e => { e.preventDefault(); uploadArea.style.borderColor = ''; if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]) });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) uploadFile(fileInput.files[0]) });
const ragInput = $('ragInput');
$('ragAsk').addEventListener('click', askQuestion);
ragInput.addEventListener('keydown', e => { if (e.key === 'Enter') askQuestion() });

function setRAGReady(ready) {
  ragInput.disabled = !ready;
  $('ragAsk').disabled = !ready;
}

async function uploadFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) { alert('Only PDF files are supported'); return }
  uploadArea.innerHTML = '<div class="spinner" style="margin:0 auto"></div><p style="margin-top:8px;color:var(--text2)">Processing...</p>';
  try {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API}/api/rag/upload`, { method: 'POST', body: form });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Upload failed') }
    await fetchDocs();
    uploadArea.innerHTML = '<div class="icon">✅</div><p style="color:var(--green)">Uploaded successfully!</p>';
    setTimeout(() => { uploadArea.innerHTML = '<div class="icon">📤</div><p>Drop a PDF here or click to upload</p>' }, 2000);
  } catch (e) {
    uploadArea.innerHTML = `<div class="icon">❌</div><p style="color:var(--red)">${e.message}</p>`;
    setTimeout(() => { uploadArea.innerHTML = '<div class="icon">📤</div><p>Drop a PDF here or click to upload</p>' }, 3000);
  }
}

async function fetchDocs() {
  try {
    const res = await fetch(`${API}/api/rag/documents`);
    const data = await res.json();
    const list = $('docList');
    if (!data.documents.length) { list.innerHTML = ''; setRAGReady(false); return }
    setRAGReady(true);
    list.innerHTML = data.documents.map(d => `
      <div class="doc-chip">
        📄 ${d.filename}
        <span style="color:var(--text2)">${d.chunks} chunks</span>
        <span class="del" onclick="deleteDoc('${d.id}')">✕</span>
      </div>`).join('');
  } catch (e) {}
}

async function deleteDoc(id) {
  try {
    await fetch(`${API}/api/rag/documents/${id}`, { method: 'DELETE' });
    fetchDocs();
  } catch (e) {}
}

async function askQuestion() {
  const q = ragInput.value.trim();
  if (!q) return;
  const answerBox = $('answerBox');
  answerBox.style.display = 'block';
  answerBox.innerHTML = '<span class="spinner"></span> Searching...';
  const askBtn = $('ragAsk');
  askBtn.disabled = true; askBtn.innerHTML = '<span class="spinner"></span>';
  try {
    const res = await fetch(`${API}/api/rag/query`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q })
    });
    const data = await res.json();
    const conf = Math.round(data.confidence * 100);
    const color = conf > 70 ? 'var(--green)' : conf > 40 ? 'var(--orange)' : 'var(--red)';
    answerBox.innerHTML = `
      <div class="conf">Confidence: <span style="color:${color}">${conf}%</span></div>
      <div>${data.answer}</div>
      ${data.sources.length ? `<div class="sources">Sources: ${data.sources.join(', ')}</div>` : ''}`;
  } catch (e) {
    answerBox.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
  askBtn.disabled = false; askBtn.textContent = 'Ask';
}

/* ─── Initial load ─── */
fetchTasks();
fetchDocs();
