import { authFetch, requireAuth, logout } from './auth.js';

// Guard — redirect to login if no token
if (!requireAuth()) throw new Error('Not authenticated');

const API_BASE_URL = "http://localhost:8000";

const form = document.getElementById("scan-form");
const walletInput = document.getElementById("wallet-address");
const blockchainSelect = document.getElementById("blockchain");
const scanButton = document.getElementById("scan-button");
const scanButtonText = document.getElementById("scan-button-text");
const scanButtonSpinner = document.getElementById("scan-button-spinner");
const formError = document.getElementById("scan-error");


const fraudScoreEl = document.getElementById("fraud-score");
const riskLevelEl = document.getElementById("risk-level");

const statWallet = document.getElementById("stat-wallet");
const statBlockchain = document.getElementById("stat-blockchain");
const statTxCount = document.getElementById("stat-tx-count");
const statAvg = document.getElementById("stat-avg");
const statMax = document.getElementById("stat-max");
const statBurst = document.getElementById("stat-burst");

const historyBody = document.getElementById("history-body");
const modelStatus = document.getElementById("model-status");

// SVG gauge: arc from left (20,110) sweeping 180° to right (180,110), radius 80, center (100,110)
const gaugeNeedle = document.getElementById("gauge-needle");

function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = (angleDeg - 90) * Math.PI / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function updateGauge(prob) {
  const cx = 100, cy = 110, r = 80;
  // prob=0 → angle=-90 (left), prob=1 → angle=90 (right)
  const startAngle = -90;
  const endAngle = startAngle + prob * 180;

  const start = polarToCartesian(cx, cy, r, startAngle);   // always (20, 110)
  const end = polarToCartesian(cx, cy, r, endAngle);

  const largeArc = 0;
  if (prob <= 0.001) {
    gaugeNeedle.setAttribute("d", `M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${start.x} ${start.y}`);
  } else {
    gaugeNeedle.setAttribute("d", `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`);
  }

  // Color the needle based on risk
  let color, label, labelFill;
  if (prob < 0.3) {
    color = "#4ade80";
    label = "Low risk";
    labelFill = "#4ade80";
  } else if (prob <= 0.7) {
    color = "#eab308";
    label = "Medium risk";
    labelFill = "#facc15";
  } else {
    color = "#fb7185";
    label = "High risk";
    labelFill = "#fb7185";
  }

  gaugeNeedle.setAttribute("stroke", color);
  fraudScoreEl.textContent = `${(prob * 100).toFixed(1)}%`;
  riskLevelEl.textContent = label;
  riskLevelEl.setAttribute("fill", labelFill);
}

function setLoading(isLoading) {
  scanButton.disabled = isLoading;
  if (isLoading) {
    scanButtonText.textContent = "Scanning...";
    scanButtonSpinner.classList.remove("hidden");
  } else {
    scanButtonText.textContent = "Scan Wallet";
    scanButtonSpinner.classList.add("hidden");
  }
}

function setFormError(message) {
  if (!message) {
    formError.classList.add("hidden");
    formError.textContent = "";
  } else {
    formError.classList.remove("hidden");
    formError.textContent = message;
  }
}

function formatValue(value, blockchain) {
  const unit = blockchain === "ethereum" ? "ETH" : "BTC";
  return `${value.toFixed(6)} ${unit}`;
}

function updateStats(scan) {
  statWallet.textContent = scan.wallet_address;
  statBlockchain.textContent =
    scan.blockchain === "ethereum" ? "Ethereum" : "Bitcoin";
  statTxCount.textContent = scan.transaction_count;
  statAvg.textContent = formatValue(scan.avg_value, scan.blockchain);
  statMax.textContent = formatValue(scan.max_value, scan.blockchain);
  statBurst.textContent = scan.burst_activity.toFixed(2);
}

function riskPill(riskLevel) {
  return `<span class="risk-pill risk-pill--${riskLevel}">${riskLevel}</span>`;
}

function shortenWallet(addr) {
  if (!addr || addr.length <= 12) return addr;
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

function formatTimestamp(ts) {
  try {
    const d = new Date(ts);
    return d.toLocaleString();
  } catch {
    return ts;
  }
}

function renderShap(shapJson) {
  const container = document.getElementById("xai-bars");
  if (!container) return;
  if (!shapJson) {
    container.innerHTML = '<p class="empty-state" style="grid-column: 1 / -1; margin: 0;">No AI explanation available.</p>';
    return;
  }

  let shapData = {};
  try { shapData = JSON.parse(shapJson); } catch (e) {}

  if (Object.keys(shapData).length === 0) {
    container.innerHTML = '<p class="empty-state" style="grid-column: 1 / -1; margin: 0;">No AI explanation available.</p>';
    return;
  }

  const entries = Object.entries(shapData).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const maxVal = Math.max(...entries.map(e => Math.abs(e[1])), 0.001);

  let html = "";
  for (const [feature, impact] of entries) {
    if (Math.abs(impact) < 0.001) continue;

    const isRisk = impact > 0;
    const color = isRisk ? "#ef4444" : "#10b981";
    const percent = Math.min(100, Math.max(2, (Math.abs(impact) / maxVal) * 100));

    html += `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; font-size: 13px; color: var(--text-soft); font-weight: 500;">
          <span style="letter-spacing: 0.02em;">${feature}</span>
          <span style="color: ${color}; font-weight: 700;">${isRisk ? '+' : ''}${impact.toFixed(3)}</span>
        </div>
        <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.04); border-radius: 4px; overflow: hidden;">
          <div style="width: ${percent}%; height: 100%; background: ${color}; border-radius: 4px; box-shadow: 0 0 10px ${color}; opacity: 0.85;"></div>
        </div>
      </div>
    `;
  }

  if (html) {
    container.innerHTML = html;
  } else {
    container.innerHTML = '<p class="empty-state" style="grid-column: 1 / -1; margin: 0;">No significant features detected.</p>';
  }
}

function renderHistory(scans) {
  if (!scans || scans.length === 0) {
    historyBody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state" style="padding: 40px!important;">No scans yet. Run your first scan above.</td>
      </tr>
    `;
    return;
  }

  historyBody.innerHTML = scans
    .map(
      (s) => `
      <tr>
        <td>${formatTimestamp(s.timestamp)}</td>
        <td title="${s.wallet_address}">${shortenWallet(s.wallet_address)}</td>
        <td>${s.blockchain === "ethereum" ? "ETH" : "BTC"}</td>
        <td>${s.transaction_count}</td>
        <td>${(s.fraud_probability * 100).toFixed(1)}%</td>
        <td>${riskPill(s.risk_level)}</td>
        <td>
          ${s.user_feedback === null ? 
            `<button onclick="window.submitFeedback(${s.scan_id}, 1)" style="padding:4px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:6px;cursor:pointer;margin-right:4px;" title="Flag as Fraud">🚩</button>
             <button onclick="window.submitFeedback(${s.scan_id}, 0)" style="padding:4px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:6px;cursor:pointer;" title="Mark as Safe">✅</button>` : 
            (s.user_feedback === 1 ? '<span title="Confirmed Fraud">🚩</span>' : '<span title="Confirmed Safe">✅</span>')
          }
        </td>
      </tr>
    `
    )
    .join("");
}

window.submitFeedback = async function(scanId, feedbackVal) {
  try {
    const res = await authFetch(`${API_BASE_URL}/flag-scan/${scanId}`, {
      method: "POST",
      body: JSON.stringify({ feedback: feedbackVal })
    });
    if (res.ok) await fetchHistory();
  } catch (err) {
    alert("Error submitting feedback: " + err.message);
  }
};

async function fetchHistory() {
  try {
    const res = await authFetch(`${API_BASE_URL}/scan-history?limit=50`);
    if (!res.ok) throw new Error("Failed to load history");
    const data = await res.json();
    renderHistory(data.scans || []);
  } catch (err) {
    console.warn("Error loading history:", err);
  }
}

async function checkBackendReady() {
  try {
    const res = await authFetch(`${API_BASE_URL}/scan-history?limit=1`);
    if (res.ok) {
      modelStatus.textContent = "Ready";
      modelStatus.className = "status-pill status-pill--ready";
    } else {
      modelStatus.textContent = "Backend error";
      modelStatus.className = "status-pill status-pill--error";
    }
  } catch {
    modelStatus.textContent = "Backend offline";
    modelStatus.className = "status-pill status-pill--error";
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  setFormError("");

  const wallet = walletInput.value.trim();
  const blockchain = blockchainSelect.value;

  if (!wallet) {
    setFormError("Please enter a wallet address.");
    return;
  }

  setLoading(true);

  try {
    const res = await authFetch(`${API_BASE_URL}/scan-wallet`, {
      method: "POST",
      body: JSON.stringify({
        wallet_address: wallet,
        blockchain,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Scan failed. Please try again.");
    }

    const scan = await res.json();
    updateGauge(scan.fraud_probability);
    updateStats(scan);
    renderShap(scan.shap_data);
    await fetchHistory();
  } catch (err) {
    console.error(err);
    setFormError(err.message || "Unexpected error during scan.");
  } finally {
    setLoading(false);
  }
});

window.addEventListener("load", () => {
  updateGauge(0);
  fetchHistory();
  checkBackendReady();

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  const retrainBtn = document.getElementById("retrain-btn");
  if (retrainBtn) {
    retrainBtn.addEventListener("click", async () => {
      const originalText = retrainBtn.innerHTML;
      retrainBtn.innerHTML = "↻ Retraining...";
      retrainBtn.disabled = true;
      try {
        const res = await authFetch(`${API_BASE_URL}/retrain`, { method: "POST" });
        if (res.ok) alert("AI successfully retrained with new feedback!");
        else alert("Failed to retrain model.");
      } catch (err) {
        alert("Error retraining: " + err.message);
      } finally {
        retrainBtn.innerHTML = originalText;
        retrainBtn.disabled = false;
      }
    });
  }

  const batchBtn = document.getElementById("batch-btn");
  const batchFile = document.getElementById("batch-file");
  if (batchBtn && batchFile) {
    batchBtn.addEventListener("click", () => batchFile.click());
    batchFile.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const formData = new FormData();
      formData.append("file", file);
      
      batchBtn.innerHTML = "↻ Processing Batch...";
      batchBtn.disabled = true;
      formError.classList.add("hidden");
      
      try {
        const res = await authFetch(`${API_BASE_URL}/scan-batch`, {
          method: "POST",
          body: formData
        });
        
        if (res.ok) {
          const data = await res.json();
          const results = data.successful || [];
          const failed = data.failed || [];
          
          let msg = `Successfully scanned ${results.length} wallets!`;
          if (failed.length > 0) {
            msg += `\nFailed to scan ${failed.length} wallets. (Check console for API rate limit errors)`;
            console.warn("Failed wallets:", failed);
          }
          alert(msg);
          await fetchHistory();
        } else {
          const err = await res.json();
          formError.textContent = "Batch Error: " + (err.detail || "Unknown error");
          formError.classList.remove("hidden");
        }
      } catch (err) {
        formError.textContent = "Error: " + err.message;
        formError.classList.remove("hidden");
      } finally {
        batchBtn.innerHTML = "Upload CSV";
        batchBtn.disabled = false;
        batchFile.value = "";
      }
    });
  }

});

