const matchesBody = document.getElementById("matchesBody");
const todayLeaderboardBody = document.getElementById("todayLeaderboardBody");
const historyLeaderboardBody = document.getElementById("historyLeaderboardBody");
const liveFeed = document.getElementById("liveFeed");
const topPlayersChart = document.getElementById("topPlayersChart");
const kpiMatches = document.getElementById("kpiMatches");
const kpiTodayPlayers = document.getElementById("kpiTodayPlayers");
const kpiLiveStatus = document.getElementById("kpiLiveStatus");

let liveSource = null;

function setLiveStatus(text, cssClass) {
  kpiLiveStatus.textContent = text;
  kpiLiveStatus.classList.remove("status-ok", "status-warn", "status-bad");
  kpiLiveStatus.classList.add(cssClass);
}

function formatDate(value) {
  return new Date(value).toLocaleString();
}

function cell(value, className) {
  const td = document.createElement("td");
  if (className) td.className = className;
  td.textContent = value;
  return td;
}

function replaceRows(tbody, rows, emptyMessage) {
  tbody.replaceChildren(...(rows.length ? rows : [rowEmpty(6, emptyMessage)]));
}

function rowMatch(m) {
  const tr = document.createElement("tr");
  tr.append(
    cell(formatDate(m.played_at)),
    cell(m.player_a),
    cell(m.throw_a),
    cell(m.player_b),
    cell(m.throw_b),
    cell(m.winner),
  );
  return tr;
}

function rowLeaderboard(r) {
  const tr = document.createElement("tr");
  tr.append(
    cell(r.player),
    cell(r.wins),
    cell(r.losses),
    cell(r.draws),
    cell(r.games),
    cell(r.win_rate),
  );
  return tr;
}

function rowEmpty(colspan, message) {
  const tr = document.createElement("tr");
  const td = cell(message, "empty");
  td.colSpan = colspan;
  tr.appendChild(td);
  return tr;
}

function chartEmpty(message) {
  const li = document.createElement("li");
  const span = document.createElement("span");
  span.className = "empty";
  span.textContent = message;
  li.appendChild(span);
  topPlayersChart.replaceChildren(li);
}

function renderTopPlayersChart(rows) {
  const topRows = [...rows].sort((a, b) => b.wins - a.wins).slice(0, 5);
  if (!topRows.length) {
    chartEmpty("No chart data for selected range.");
    return;
  }
  const maxWins = Math.max(...topRows.map((r) => r.wins), 1);
  topPlayersChart.replaceChildren(
    ...topRows.map((row) => {
      const width = Math.max(6, Math.round((row.wins / maxWins) * 100));
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = row.player;
      const barWrap = document.createElement("span");
      barWrap.className = "bar-wrap";
      const bar = document.createElement("span");
      bar.className = "bar";
      bar.style.width = `${width}%`;
      barWrap.appendChild(bar);
      const value = document.createElement("span");
      value.className = "value";
      value.textContent = row.wins;
      li.append(name, barWrap, value);
      return li;
    }),
  );
}

function paramsFromFilters() {
  const player = document.getElementById("player").value.trim();
  const date = document.getElementById("date").value;
  const startDate = document.getElementById("startDate").value;
  const endDate = document.getElementById("endDate").value;
  const params = new URLSearchParams();
  if (player) params.set("player", player);
  if (date) params.set("date", date);
  if (startDate) params.set("startDate", startDate);
  if (endDate) params.set("endDate", endDate);
  params.set("take", "50");
  return params;
}

async function loadMatches() {
  const params = paramsFromFilters();
  try {
    const res = await fetch(`/api/matches/history?${params.toString()}`);
    if (!res.ok) throw new Error(`history failed (${res.status})`);
    const json = await res.json();
    const rows = json.data || [];
    replaceRows(matchesBody, rows.map(rowMatch), "No matches for current filter.");
    kpiMatches.textContent = String(rows.length);
  } catch (error) {
    matchesBody.replaceChildren(rowEmpty(6, "Failed to load matches."));
    kpiMatches.textContent = "0";
    console.error(error);
  }
}

async function loadTodayLeaderboard() {
  try {
    const res = await fetch("/api/leaderboard/today");
    if (!res.ok) throw new Error(`today leaderboard failed (${res.status})`);
    const json = await res.json();
    const rows = json.data || [];
    replaceRows(todayLeaderboardBody, rows.map(rowLeaderboard), "No players found today.");
    kpiTodayPlayers.textContent = String(rows.length);
  } catch (error) {
    todayLeaderboardBody.replaceChildren(rowEmpty(6, "Failed to load today leaderboard."));
    kpiTodayPlayers.textContent = "0";
    console.error(error);
  }
}

async function loadHistoryLeaderboard() {
  const params = paramsFromFilters();
  params.delete("player");
  params.delete("take");
  try {
    const res = await fetch(`/api/leaderboard/history?${params.toString()}`);
    if (!res.ok) throw new Error(`history leaderboard failed (${res.status})`);
    const json = await res.json();
    const rows = json.data || [];
    replaceRows(historyLeaderboardBody, rows.map(rowLeaderboard), "No players for selected range.");
    renderTopPlayersChart(rows);
  } catch (error) {
    historyLeaderboardBody.replaceChildren(rowEmpty(6, "Failed to load historical leaderboard."));
    chartEmpty("Failed to load chart data.");
    console.error(error);
  }
}

function wireLiveFeed() {
  if (liveSource) {
    liveSource.close();
  }
  setLiveStatus("Connecting", "status-warn");
  liveSource = new EventSource("/api/live");

  liveSource.onopen = () => {
    setLiveStatus("Connected", "status-ok");
  };

  liveSource.onmessage = (event) => {
    let rendered = event.data;
    try {
      const parsed = JSON.parse(event.data);
      if (parsed && parsed.playerA && parsed.playerB) {
        rendered = `${parsed.playerA.name} (${parsed.playerA.played}) vs ${parsed.playerB.name} (${parsed.playerB.played})`;
      }
    } catch (_e) {
      // Keep plain text payloads as-is.
    }
    const li = document.createElement("li");
    li.textContent = rendered;
    liveFeed.prepend(li);
    while (liveFeed.children.length > 25) {
      liveFeed.removeChild(liveFeed.lastChild);
    }
  };

  liveSource.onerror = () => {
    // EventSource reconnects automatically; show degraded status only.
    setLiveStatus("Reconnecting", "status-warn");
  };
}

async function refreshAll() {
  await Promise.all([loadMatches(), loadTodayLeaderboard(), loadHistoryLeaderboard()]);
}

document.getElementById("filters").addEventListener("submit", async (event) => {
  event.preventDefault();
  await refreshAll();
});

document.getElementById("clearFilters").addEventListener("click", async () => {
  document.getElementById("player").value = "";
  document.getElementById("date").value = "";
  document.getElementById("startDate").value = "";
  document.getElementById("endDate").value = "";
  await refreshAll();
});

window.addEventListener("beforeunload", () => {
  if (liveSource) {
    liveSource.close();
  }
});

refreshAll().then(wireLiveFeed);
