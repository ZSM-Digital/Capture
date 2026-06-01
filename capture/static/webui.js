function esc(s) {
  if (s === undefined || s === null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/"/g, "&quot;");
}

function hostLabel(url) {
  if (!url) return "";
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

function safeHrefUrl(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    return parsed.href;
  } catch {
    return null;
  }
}

function urlCell(url, links, label) {
  if (!url) return "—";
  const text = label || url;
  const href = links ? safeHrefUrl(url) : null;
  if (href) {
    return (
      '<a href="' +
      esc(href) +
      '" target="_blank" rel="noopener noreferrer">' +
      esc(text) +
      "</a>"
    );
  }
  return '<span class="url">' + esc(text) + "</span>";
}

function entrySource(e) {
  return e.source_url || null;
}

function entryImage(e) {
  return e.image_url || null;
}

async function load() {
  const statusEl = document.getElementById("status");
  try {
    const res = await fetch("/webui/api/requests");
    if (!res.ok) throw new Error(res.status + " " + res.statusText);
    const data = await res.json();
    const rows = document.getElementById("rows");
    rows.innerHTML = "";
    const cutoff = Date.now() - 5 * 60 * 1000;
    let recent = 0;
    const links = !!data.links;
    const entries = Array.isArray(data.entries)
      ? data.entries.slice().reverse()
      : [];
    if (entries.length === 0) {
      const tr = document.createElement("tr");
      tr.className = "empty";
      tr.innerHTML = '<td colspan="5">No captures yet</td>';
      rows.appendChild(tr);
    }
    for (const e of entries) {
      const src = entrySource(e);
      const img = entryImage(e);
      const t = new Date(e.ts * 1000).toLocaleTimeString();
      let status = String(e.status);
      if (e.error) status += " · " + esc(e.error);
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        t +
        "</td>" +
        "<td>" +
        urlCell(src, links, src ? hostLabel(src) : null) +
        "</td>" +
        "<td>" +
        urlCell(img, links, "view") +
        "</td>" +
        '<td class="s' +
        Math.floor(e.status / 100) +
        'xx">' +
        status +
        "</td>" +
        '<td class="muted">' +
        esc(e.client || "-") +
        "</td>";
      rows.appendChild(tr);
      if (e.ts * 1000 >= cutoff) recent++;
    }
    document.getElementById("total").textContent = data.total;
    document.getElementById("recent").textContent = recent;
    statusEl.textContent = "ok";
    statusEl.className = "s2xx";
  } catch (err) {
    statusEl.textContent = String(err);
    statusEl.className = "s5xx";
  }
}
load();
setInterval(load, 2000);
