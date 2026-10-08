let selected = [];
const logEl = document.getElementById("log");
const filesEl = document.getElementById("files");
const agentsEl = document.getElementById("agents");

function addLog(msg) {
  const d = document.createElement("div");
  d.textContent = msg;
  logEl.appendChild(d);
  logEl.scrollTop = logEl.scrollHeight;
}

async function loadAgents() {
  const r = await fetch("/api/agents");
  const data = await r.json();
  for (const [key, a] of Object.entries(data)) {
    const c = document.createElement("div");
    c.className = "chip";
    c.textContent = a.role;
    c.onclick = () => toggle(key, c);
    c.dataset.key = key;
    agentsEl.appendChild(c);
  }
}

function toggle(key, el) {
  const i = selected.indexOf(key);
  if (i >= 0) { selected.splice(i, 1); el.classList.remove("sel"); }
  else { selected.push(key); el.classList.add("sel"); }
  document.getElementById("pipelineInfo").textContent =
    selected.length ? "Pipeline: " + selected.join(" → ") : "Pipeline: auto (dipilih LLM)";
}

async function send() {
  const objective = document.getElementById("obj").value.trim();
  if (!objective) return alert("Isi objektif dulu!");
  document.getElementById("go").disabled = true;
  logEl.innerHTML = "";
  const body = { objective };
  if (selected.length) body.pipeline = selected;
  const r = await fetch("/api/command", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  addLog("📌 Pipeline dimulai: " + data.pipeline.join(" → "));
  pollFiles();
}

async function pollFiles() {
  try {
    const r = await fetch("/api/workspace");
    const { files } = await r.json();
    filesEl.innerHTML = "";
    for (const f of files) {
      const a = document.createElement("a");
      a.href = "/api/workspace/file?name=" + encodeURIComponent(f);
      a.textContent = "📄 " + f;
      a.target = "_blank";
      filesEl.appendChild(a);
    }
  } catch (e) {}
}

function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => document.getElementById("wsdot").classList.add("on");
  ws.onclose = () => {
    document.getElementById("wsdot").classList.remove("on");
    setTimeout(connectWS, 2000);
  };
  ws.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    addLog(d.msg);
    if (d.msg.startsWith("🏁")) {
      document.getElementById("go").disabled = false;
      pollFiles();
    }
  };
}

loadAgents();
connectWS();
pollFiles();
