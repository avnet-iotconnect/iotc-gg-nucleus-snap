const panels = document.querySelectorAll(".panel");
const segmentButtons = document.querySelectorAll(".segment");
const kitForm = document.getElementById("kitForm");
const manualForm = document.getElementById("manualForm");
const onboardMessage = document.getElementById("onboardMessage");
const runsContainer = document.getElementById("runs");
const logTail = document.getElementById("logTail");
const refreshBtn = document.getElementById("refreshStatus");
const commandButtons = document.querySelectorAll("[data-action]");
const lastUpdated = document.getElementById("lastUpdated");
const directActions = new Set(["start", "stop", "restart", "kill"]);
const snapActions = new Set(["snap-start", "snap-stop", "snap-restart"]);

const processStatus = document.getElementById("processStatus");
const processDetail = document.getElementById("processDetail");
const deploymentStatus = document.getElementById("deploymentStatus");
const deploymentDetail = document.getElementById("deploymentDetail");
const lastError = document.getElementById("lastError");
const rootPath = document.getElementById("rootPath");

const rootInputs = Array.from(document.querySelectorAll("input[name='greengrassRoot']"));

function getRootValue() {
  const filled = rootInputs.find((input) => input.value.trim());
  return filled ? filled.value.trim() : "";
}

function setMessage(text, isError = false) {
  onboardMessage.textContent = text;
  onboardMessage.style.color = isError ? "#f87171" : "#9ca3af";
}

function setCommandAvailability(root, snapInstall) {
  const isSnap = snapInstall || (root && root.includes("/var/snap/"));
  commandButtons.forEach((button) => {
    const action = button.dataset.action;
    if (directActions.has(action)) {
      button.disabled = isSnap;
      button.title = isSnap ? "Snap install detected. Use Snap Start/Stop/Restart." : "";
    }
    if (snapActions.has(action)) {
      button.disabled = !isSnap;
      button.title = !isSnap ? "Snap actions available only for snap installs." : "";
    }
  });
}

segmentButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    segmentButtons.forEach((b) => b.classList.remove("active"));
    panels.forEach((panel) => panel.classList.remove("active"));
    btn.classList.add("active");
    const panel = document.getElementById(`panel-${btn.dataset.panel}`);
    if (panel) panel.classList.add("active");
  });
});

async function fetchRoots() {
  try {
    const res = await fetch("/api/roots");
    const data = await res.json();
    const list = document.getElementById("rootCandidates");
    list.innerHTML = "";
    data.roots.forEach((root) => {
      const option = document.createElement("option");
      option.value = root;
      list.appendChild(option);
    });

    if (data.roots.length && !getRootValue()) {
      rootInputs.forEach((input) => {
        if (!input.value.trim()) {
          input.value = data.roots[0];
        }
      });
    }
  } catch (err) {
    setMessage("Failed to load root suggestions.", true);
  }
}

async function refreshStatus() {
  const root = getRootValue();
  const url = root ? `/api/status?root=${encodeURIComponent(root)}` : "/api/status";

  try {
    const res = await fetch(url);
    const data = await res.json();
    rootPath.textContent = data.root;
    setCommandAvailability(data.root, data.snapInstall);

    processStatus.textContent = data.process.running ? "Running" : "Stopped";
    processStatus.style.color = data.process.running ? "#6ee7b7" : "#f87171";
    const entry = data.process.entries[0];
    processDetail.textContent = entry ? `${entry.pid} ${entry.cmd}` : "No process found";

    deploymentStatus.textContent = data.deployment.state.replace(/_/g, " ");
    deploymentDetail.textContent = data.deployment.detail;

    lastError.textContent = data.lastError || "No recent errors";
    lastUpdated.textContent = data.updatedAt || "—";
  } catch (err) {
    setMessage("Failed to refresh status.", true);
  }
}

async function refreshLogs(manual = false) {
  const root = getRootValue();
  const modeParam = manual ? "&mode=manual" : "";
  const url = root ? `/api/logs?root=${encodeURIComponent(root)}${modeParam}` : `/api/logs?mode=${manual ? "manual" : "auto"}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    const sourceLabel = data.source ? `(${data.source})` : "";
    if (data.lines.length) {
      logTail.textContent = data.lines.join("\n");
    } else if (data.error) {
      logTail.textContent = `Unable to read logs ${sourceLabel}: ${data.error}`;
    } else {
      logTail.textContent = `No log entries yet ${sourceLabel}.`;
    }
  } catch (err) {
    logTail.textContent = "Unable to read logs.";
  }
}

async function refreshRuns() {
  try {
    const res = await fetch("/api/runs");
    const data = await res.json();
    if (!data.runs.length) {
      runsContainer.innerHTML = '<p class="empty">No runs yet.</p>';
      return;
    }

    runsContainer.innerHTML = "";
    data.runs
      .slice()
      .reverse()
      .forEach((run) => {
        const div = document.createElement("div");
        div.className = `run ${run.status}`;
        const statusLabel = run.status === "running" ? "Running" : run.status;
        div.innerHTML = `
          <span class="status-pill">${statusLabel}</span>
          <div class="mono">${run.cmd.join(" ")}</div>
          <div class="detail">Started: ${run.startedAt}</div>
          <div class="detail">Finished: ${run.finishedAt || "—"}</div>
          <div class="detail mono">Exit: ${run.returnCode ?? "—"}</div>
        `;
        runsContainer.appendChild(div);
      });
  } catch (err) {
    runsContainer.innerHTML = '<p class="empty">Failed to load runs.</p>';
  }
}

kitForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Uploading kit and starting onboarding...");

  const formData = new FormData(kitForm);
  try {
    const res = await fetch("/api/onboard/connection-kit", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Failed to start onboarding");
    }
    setMessage(`Onboarding started. Run ID: ${data.runId}`);
    kitForm.reset();
  } catch (err) {
    setMessage(err.message, true);
  }
});

manualForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Starting onboarding...");

  const formData = new FormData(manualForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const res = await fetch("/api/onboard/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Failed to start onboarding");
    }
    setMessage(`Onboarding started. Run ID: ${data.runId}`);
    manualForm.reset();
  } catch (err) {
    setMessage(err.message, true);
  }
});

refreshBtn.addEventListener("click", () => {
  refreshStatus();
  refreshLogs(true);
});

commandButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const action = button.dataset.action;
    setMessage(`${action} command sent...`);

    try {
      const res = await fetch("/api/process/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          greengrassRoot: getRootValue(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.message || "Command failed");
      }
      setMessage(data.message || "Command completed.");
      refreshStatus();
      refreshLogs();
    } catch (err) {
      setMessage(err.message, true);
    }
  });
});

fetchRoots();
refreshStatus();
refreshRuns();

setInterval(() => {
  refreshStatus();
  refreshRuns();
}, 5000);
