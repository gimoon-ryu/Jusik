async function loadCsv(path) {
  const response = await fetch(`${path}?v=${Date.now()}`);
  if (!response.ok) {
    return [];
  }
  const text = await response.text();
  return parseCsv(text);
}

function parseCsv(text) {
  const rows = [];
  let cell = "";
  let row = [];
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) {
        rows.push(row);
      }
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }

  if (!rows.length) {
    return [];
  }

  const headers = rows[0];
  return rows.slice(1).map((values) => {
    const record = {};
    headers.forEach((header, index) => {
      record[header] = values[index] || "";
    });
    return record;
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function tradingValueLabel(value) {
  const number = Number(value || 0);
  return `${Math.round(number / 100000000).toLocaleString("ko-KR")}억`;
}

function renderScores(scores) {
  const rows = document.getElementById("scoreRows");
  const updatedAt = document.getElementById("updatedAt");
  const stockCount = document.getElementById("stockCount");
  const topScore = document.getElementById("topScore");

  if (!scores.length) {
    rows.innerHTML = '<tr><td colspan="10">아직 점수 데이터가 없습니다.</td></tr>';
    return;
  }

  updatedAt.textContent = scores[0].updated_at || "-";
  stockCount.textContent = String(scores.length);
  topScore.textContent = scores[0].final_score || "-";
  rows.innerHTML = scores.slice(0, 50).map((row, index) => `
    <tr>
      <td>${index + 1}</td>
      <td><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.ticker)}</small></td>
      <td><b>${escapeHtml(row.final_score)}</b></td>
      <td>${escapeHtml(row.change_rate)}%</td>
      <td>${tradingValueLabel(row.trading_value)}</td>
      <td>${escapeHtml(row.relative_strength_score)}</td>
      <td>${escapeHtml(row.trading_value_score)}</td>
      <td>${escapeHtml(row.etf_exposure_score)}</td>
      <td>${escapeHtml(row.growth_score)}</td>
      <td>${escapeHtml(row.thesis)}</td>
    </tr>
  `).join("");
}

function renderEvents(events) {
  const container = document.getElementById("eventRows");
  if (!events.length) {
    container.innerHTML = "<p>업데이트 이력이 없습니다.</p>";
    return;
  }
  container.innerHTML = events.slice(-5).reverse().map((row) => `
    <p><strong>${escapeHtml(row.updated_at)}</strong> <span>${escapeHtml(row.status)}</span> ${escapeHtml(row.message)} (${escapeHtml(row.count)}개)</p>
  `).join("");
}

async function main() {
  const [scores, events] = await Promise.all([
    loadCsv("data/krx_scores.csv"),
    loadCsv("data/krx_events.csv")
  ]);
  renderScores(scores);
  renderEvents(events);
}

main();

