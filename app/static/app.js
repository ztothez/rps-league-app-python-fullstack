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

function rowMatch(m) {
  return `<tr>
    <td>${formatDate(m.played_at)}</td>
    <td>${m.player_a}</td>
    <td>${m.throw_a}</td>
    <td>${m.player_b}</td>
    <td>${m.throw_b}</td>
    <td>${m.winner}</td>
  </tr>`;
}

function rowLeaderboard(r) {
  return `<tr>
    <td>${r.player}</td>
    <td>${r.wins}</td>
    <td>${r.losses}</td>
    <td>${r.draws}</td>
    <td>${r.games}</td>
    <td>${r.win_rate}</td>
  </tr>`;
}

function rowEmpty(colspan, message) {
  return `<tr><td class="empty" colspan="${colspan}">${message}</td></tr>`;
}

function chartEmpty(message) {
  topPlayersChart.innerHTML = `<li><span class="empty">${message}</span></li>`;
}

function renderTopPlayersChart(rows) {
  const topRows = [...rows].sort((a, b) => b.wins - a.wins).slice(0, 5);
  if (!topRows.length) {
    chartEmpty("No chart data for selected range.");
    return;
  }
  const maxWins = Math.max(...topRows.map((r) => r.wins), 1);
  topPlayersChart.innerHTML = topRows
    .map((row) => {
      const width = Math.max(6, Math.round((row.wins / maxWins) * 100));
      return `<li>
        <span class="name">${row.player}</span>
        <span class="bar-wrap"><span class="bar" style="width:${width}%"></span></span>
        <span class="value">${row.wins}</span>
      </li>`;
    })
    .join("");
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
    matchesBody.innerHTML = rows.length
      ? rows.map(rowMatch).join("")
      : rowEmpty(6, "No matches for current filter.");
    kpiMatches.textContent = String(rows.length);
  } catch (error) {
    matchesBody.innerHTML = rowEmpty(6, "Failed to load matches.");
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
    todayLeaderboardBody.innerHTML = rows.length
      ? rows.map(rowLeaderboard).join("")
      : rowEmpty(6, "No players found today.");
    kpiTodayPlayers.textContent = String(rows.length);
  } catch (error) {
    todayLeaderboardBody.innerHTML = rowEmpty(6, "Failed to load today leaderboard.");
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
    historyLeaderboardBody.innerHTML = rows.length
      ? rows.map(rowLeaderboard).join("")
      : rowEmpty(6, "No players for selected range.");
    renderTopPlayersChart(rows);
  } catch (error) {
    historyLeaderboardBody.innerHTML = rowEmpty(6, "Failed to load historical leaderboard.");
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
