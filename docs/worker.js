/* Pyodide işçisi: Python mühərriki brauzerdə (serversiz) işləyir — mətn heç yerə göndərilmir. */
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");

let py = null;

async function boot() {
  py = await loadPyodide();
  const manifest = await (await fetch("manifest.json?v=" + Date.now())).json();
  py.FS.mkdirTree("/app/azhum");
  for (const f of manifest.py) {
    const txt = await (await fetch(f + "?v=" + manifest.version)).text();
    py.FS.writeFile("/app/" + f.replace(/^py\//, ""), txt);
  }
  const lex = [];
  let phrases = "";
  let det = "";
  for (const f of manifest.data) {
    const txt = await (await fetch(f + "?v=" + manifest.version)).text();
    if (/phrases_.*\.txt$/.test(f)) phrases += txt + "\n";
    else if (/lex_.*\.txt$/.test(f)) lex.push(txt);
    else if (f.endsWith("detector.json")) det = txt;
  }
  py.globals.set("LEX_JSON", JSON.stringify(lex));
  py.globals.set("PHRASES", phrases);
  py.globals.set("DET_JSON", det);
  const info = await py.runPythonAsync(`
import sys, json
sys.path.insert(0, "/app")
from azhum import web_api
web_api.init(LEX_JSON, PHRASES, DET_JSON)
`);
  return JSON.parse(info);
}

const ready = boot().then((info) => {
  postMessage({ type: "ready", info });
}).catch((e) => postMessage({ type: "error", message: String(e) }));

onmessage = async (ev) => {
  await ready;
  const m = ev.data;
  try {
    if (m.type === "run") {
      py.globals.set("IN_TEXT", m.text);
      py.globals.set("IN_LEVEL", m.level);
      py.globals.set("IN_SEED", m.seed);
      py.globals.set("IN_CAND", m.candidates);
      py.globals.set("IN_PROT", JSON.stringify(m.protected || []));
      py.globals.set("IN_TARGET", m.target || 10);
      py.globals.set("IN_FMT", m.fmt || "plain");
      py.globals.set("IN_NOISE", !!m.noise);
      const out = await py.runPythonAsync(
        "web_api.run(IN_TEXT, IN_LEVEL, int(IN_SEED), int(IN_CAND), IN_PROT, float(IN_TARGET), IN_FMT, bool(IN_NOISE))"
      );
      postMessage({ type: "result", id: m.id, data: JSON.parse(out) });
    } else if (m.type === "score") {
      py.globals.set("IN_TEXT", m.text);
      const out = await py.runPythonAsync("web_api.check_only(IN_TEXT)");
      postMessage({ type: "score", id: m.id, data: JSON.parse(out) });
    } else if (m.type === "llm_run") {
      // Server-tərəfli LLM-yenidənyazma addımı — bax: docs/index.html-dəki LLM_ENDPOINT
      // qeydi. Mətn burada (yalnız bu addımda) endpoint-ə göndərilir; qalan bütün
      // emal (struktur/səs-küyü) brauzerdə qalır.
      if (!m.endpoint) {
        postMessage({ type: "error", id: m.id, message: "LLM addımı hələ aktiv deyil: server endpoint konfiqurasiya olunmayıb." });
        return;
      }
      const resp = await fetch(m.endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: m.text }),
      });
      const respData = await resp.json();
      if (!resp.ok) {
        postMessage({ type: "error", id: m.id, message: respData.error || ("Server xətası: " + resp.status) });
        return;
      }
      py.globals.set("IN_ORIG_TEXT", m.text);
      py.globals.set("IN_LLM_TEXT", respData.rewrittenText);
      py.globals.set("IN_SEED", m.seed || 1);
      py.globals.set("IN_FMT", m.fmt || "plain");
      py.globals.set("IN_NOISE", m.noise !== false);
      const out = await py.runPythonAsync(
        "web_api.finalize_llm_text(IN_ORIG_TEXT, IN_LLM_TEXT, int(IN_SEED), IN_FMT, bool(IN_NOISE))"
      );
      postMessage({ type: "result", id: m.id, data: JSON.parse(out) });
    }
  } catch (e) {
    postMessage({ type: "error", id: m.id, message: String(e) });
  }
};
