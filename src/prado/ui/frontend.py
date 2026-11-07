"""
PradoOS Compact Setup & Quick-Configure Window (Single-Screen Native Card).

Designed following the Dropbox / Tailscale / Google Drive Desktop philosophy:
- All daily actions live in the OS Menu Bar / System Tray with native submenus.
- This compact single-card window (520x630px) opens ONLY on first run, when the user
  clicks "Configurar Cuenta UGR...", or when UGR SAML requests a 6-digit MFA code.
"""

from __future__ import annotations


def render_control_center_html(token: str) -> str:
    """Returns the self-contained HTML/CSS/JS for the compact PradoOS Setup Card."""
    return _HTML_TEMPLATE.replace("__PRADO_SESSION_TOKEN__", token)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PradoOS — Configuración UGR</title>
<style>
  :root {
    --bg-app: #0f1117;
    --bg-card: #171a23;
    --bg-input: #11131b;
    --border: #272b3a;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --accent: #e11d48;
    --accent-hover: #be123c;
    --green: #10b981;
    --green-soft: rgba(16, 185, 129, 0.14);
    --amber: #f59e0b;
    --amber-soft: rgba(245, 158, 11, 0.14);
    --red: #ef4444;
    --red-soft: rgba(239, 68, 68, 0.14);
    --radius: 12px;
  }
  @media (prefers-color-scheme: light) {
    :root {
      --bg-app: #f3f4f6;
      --bg-card: #ffffff;
      --bg-input: #f9fafb;
      --border: #e5e7eb;
      --text-main: #111827;
      --text-muted: #4b5563;
    }
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    background: var(--bg-app);
    color: var(--text-main);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding: 18px;
    user-select: none;
    -webkit-font-smoothing: antialiased;
  }
  .setup-card {
    width: 100%;
    max-width: 490px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 22px 24px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.35);
    display: flex;
    flex-direction: column;
    gap: 15px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 11px;
  }
  .brand-logo {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #e11d48, #9f1239);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
    color: #fff;
  }
  .brand-title { font-size: 16.5px; font-weight: 700; letter-spacing: -0.02em; }
  .brand-sub { font-size: 11.5px; color: var(--text-muted); margin-top: 1px; }
  .lang-row {
    display: flex;
    gap: 4px;
  }
  .lang-btn {
    padding: 4px 7px;
    font-size: 11px;
    font-weight: 600;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg-input);
    color: var(--text-muted);
    cursor: pointer;
  }
  .lang-btn.active {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }
  .status-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 12px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 9px;
    font-size: 12px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
    white-space: nowrap;
  }
  .badge-idle { background: var(--green-soft); color: var(--green); }
  .badge-syncing { background: var(--amber-soft); color: var(--amber); }
  .badge-error { background: var(--red-soft); color: var(--red); }
  .grid-2 {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 10px;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .form-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .form-hint {
    font-size: 11px;
    color: var(--text-muted);
    opacity: 0.85;
  }
  .input, .select {
    width: 100%;
    padding: 8.5px 11px;
    background: var(--bg-input);
    color: var(--text-main);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 13px;
    outline: none;
  }
  .input:focus, .select:focus { border-color: var(--accent); }
  .row { display: flex; align-items: center; gap: 8px; }
  .section-box {
    padding: 11px 13px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .check-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    font-weight: 500;
    cursor: pointer;
  }
  .check-row input { width: 15px; height: 15px; cursor: pointer; }
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 9px 15px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s ease;
    white-space: nowrap;
  }
  .btn:disabled { opacity: 0.55; cursor: not-allowed; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
  .btn-secondary {
    background: var(--bg-input);
    color: var(--text-main);
    border-color: var(--border);
  }
  .progress-wrap {
    display: none;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 9px;
  }
  .progress-wrap.visible { display: flex; }
  .progress-bar-bg {
    width: 100%;
    height: 7px;
    background: var(--border);
    border-radius: 999px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--amber));
    width: 0%;
    transition: width 0.25s ease;
  }
  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }
  /* MFA 6-digit modal overlay */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(4px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
    padding: 18px;
  }
  .modal-backdrop.visible { display: flex; }
  .modal-card {
    width: 100%;
    max-width: 410px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.55);
  }
  .toast {
    position: fixed;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    background: #111827;
    color: #fff;
    border: 1px solid var(--border);
    padding: 9px 14px;
    border-radius: 9px;
    font-size: 12.5px;
    font-weight: 500;
    display: none;
    z-index: 200;
  }
  .toast.visible { display: block; }
  .sr-only { display: none; }
</style>
</head>
<body>

  <!-- SINGLE COMPACT SETUP CARD -->
  <div class="setup-card" id="onboardingModal">
    <!-- Top Header -->
    <div class="header">
      <div class="brand">
        <div class="brand-logo">🎓</div>
        <div>
          <div class="brand-title" data-i18n="dash_title">PradoOS — Configuración UGR</div>
          <div class="brand-sub" id="versionLabel">Barra de Menús / System Tray • UGR</div>
        </div>
      </div>
      <div class="lang-row">
        <button class="lang-btn active" id="lang-es" onclick="setLanguage('es')">ES</button>
        <button class="lang-btn" id="lang-en" onclick="setLanguage('en')">EN</button>
        <button class="lang-btn" id="lang-it" onclick="setLanguage('it')">IT</button>
        <button class="lang-btn" id="lang-fr" onclick="setLanguage('fr')">FR</button>
      </div>
    </div>

    <!-- Live Status Pill -->
    <div class="status-strip">
      <span id="sidebarUser" style="font-weight:600;">🔴 Sin sesión UGR</span>
      <span class="badge badge-idle" id="syncStatusBadge">🟢 Al día</span>
    </div>

    <!-- 1. UGR Credentials & Portal -->
    <div class="grid-2">
      <div class="form-group">
        <label class="form-label" data-i18n="onb_email">Correo Institucional UGR</label>
        <input type="email" class="input" id="onbUsername" placeholder="usuario@correo.ugr.es">
      </div>
      <div class="form-group">
        <label class="form-label" data-i18n="onb_portal">Portal PRADO</label>
        <select class="select" id="onbPortal">
          <option value="grado">Grado (pradogrado)</option>
          <option value="posgrado">Posgrado / Máster</option>
          <option value="ceprud">CEPRUD / Otros</option>
        </select>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">
        <span data-i18n="onb_password">Contraseña PRADO (Acceso Identificado)</span>
        <span class="form-hint" data-i18n="keychain_hint">🔒 Guardada en Llavero nativo</span>
      </label>
      <input type="password" class="input" id="onbPassword" placeholder="••••••••••••••••">
    </div>

    <!-- 2. Destination Folder & Organization Mode -->
    <div class="form-group">
      <label class="form-label" data-i18n="onb_folder">Carpeta Local de Apuntes</label>
      <div class="row">
        <input type="text" class="input" id="onbCoursesRoot" placeholder="~/Documents/UGR_Courses">
        <button class="btn btn-secondary" onclick="pickFolderFor('onbCoursesRoot')">📂 <span data-i18n="btn_browse">Elegir...</span></button>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label" data-i18n="lbl_preset_mode">Organización de Carpetas</label>
      <select class="select" id="onbPreset">
        <option value="mirror">Mirror — Estructura oficial de cada profesor en PRADO</option>
        <option value="smart">Smart — Separar automáticamente Teoría / Prácticas / General</option>
      </select>
    </div>

    <!-- 3. Optional Mail Auto-Forwarding & Background Preferences -->
    <div class="section-box">
      <label class="check-row">
        <input type="checkbox" id="cfgFwdEnabled">
        <span data-i18n="lbl_fwd_enable">Reenviar correos de profesores (@correo.ugr.es) a mi correo personal:</span>
      </label>
      <input type="email" class="input" id="cfgFwdTo" placeholder="tu.correo@gmail.com / @icloud.com">

      <div class="row" style="justify-content:space-between; padding-top:4px;">
        <label class="check-row">
          <input type="checkbox" id="onbNotifications" checked>
          <span data-i18n="lbl_notif_title">Notificaciones de escritorio</span>
        </label>
        <span style="font-size:11.5px; color:var(--text-muted);" id="lastSyncLabel">Última sinc.: --:--</span>
      </div>
    </div>

    <!-- Inline Progress Bar (visible during sync) -->
    <div class="progress-wrap" id="syncProgressWrap">
      <div style="display:flex; justify-content:space-between; font-size:12px;">
        <span id="syncStepText">Sincronizando con PRADO UGR...</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="syncProgressBar"></div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="footer">
      <button class="btn btn-secondary" onclick="openCoursesFolder()">📂 <span data-i18n="btn_open_folder">Abrir Carpeta</span></button>
      <button class="btn btn-primary" onclick="submitCompactSetup()" id="btnSyncNow">🚀 <span data-i18n="onb_submit">Guardar y Sincronizar</span></button>
    </div>
  </div>

  <!-- LIVE 6-DIGIT MFA VERIFICATION MODAL -->
  <div class="modal-backdrop" id="mfaModal">
    <div class="modal-card">
      <div style="font-size:16px; font-weight:700; margin-bottom:8px;">🔐 Verificación en 2 Pasos (MFA UGR)</div>
      <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:14px;" id="mfaPromptText">
        Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es. Tu dispositivo quedará verificado por 30 días.
      </p>
      <div class="form-group">
        <input type="text" maxlength="6" class="input" id="mfaCodeInput" placeholder="123456" style="font-size:22px; text-align:center; letter-spacing:8px; font-weight:700;">
      </div>
      <div class="row" style="margin-top:14px;">
        <button class="btn btn-primary" onclick="submitMfaCode()" style="width:100%;">✓ Verificar Dispositivo (30 días)</button>
      </div>
    </div>
  </div>

  <!-- Hidden compatibility containers for programmatic API / E2E introspection -->
  <div class="sr-only">
    <span id="kpiCourses">0/0</span>
    <span id="kpiFiles">0</span>
    <span id="kpiProtected">0</span>
    <span id="kpiDeadlines">0</span>
    <div id="view-dashboard" class="active"></div>
    <div id="view-courses"><div id="coursesManageList"></div></div>
    <div id="view-mail"><div id="mailListPane"></div></div>
    <div id="view-calendar"><div id="doctorProbesList"></div></div>
    <select id="onbLanguage"><option value="es">es</option><option value="en">en</option><option value="it">it</option><option value="fr">fr</option></select>
  </div>

  <div class="toast" id="toastBox"></div>

<script>
const PRADO_TOKEN = "__PRADO_SESSION_TOKEN__";
let appState = null;
let currentLang = "es";
let formInitialized = false;

const I18N = {
  es: {
    dash_title: "PradoOS — Configuración UGR",
    onb_email: "Correo Institucional UGR",
    onb_portal: "Portal PRADO",
    onb_password: "Contraseña PRADO (Acceso Identificado)",
    keychain_hint: "🔒 Guardada en Llavero nativo",
    onb_folder: "Carpeta Local de Apuntes",
    btn_browse: "Elegir...",
    lbl_preset_mode: "Organización de Carpetas",
    lbl_fwd_enable: "Reenviar correos de profesores (@correo.ugr.es) a mi correo personal:",
    lbl_notif_title: "Notificaciones de escritorio",
    btn_open_folder: "Abrir Carpeta",
    onb_submit: "Guardar y Sincronizar"
  },
  en: {
    dash_title: "PradoOS — UGR Setup",
    onb_email: "UGR Institutional Email",
    onb_portal: "PRADO Portal",
    onb_password: "PRADO Password (SSO)",
    keychain_hint: "🔒 Stored in OS Keychain",
    onb_folder: "Local Courses Folder",
    btn_browse: "Browse...",
    lbl_preset_mode: "Folder Organization",
    lbl_fwd_enable: "Auto-forward professor emails (@correo.ugr.es) to my personal email:",
    lbl_notif_title: "Desktop notifications",
    btn_open_folder: "Open Folder",
    onb_submit: "Save & Sync Now"
  },
  it: {
    dash_title: "PradoOS — Centro di Controllo PRADO UGR",
    onb_email: "Email Istituzionale UGR",
    onb_portal: "Portale PRADO",
    onb_password: "Password PRADO (SSO)",
    keychain_hint: "🔒 Salvata nel Portachiavi nativo",
    onb_folder: "Cartella Locale Appunti",
    btn_browse: "Sfoglia...",
    lbl_preset_mode: "Organizzazione Cartelle",
    lbl_fwd_enable: "Inoltra email dei docenti (@correo.ugr.es) alla mia email personale:",
    lbl_notif_title: "Notifiche desktop",
    btn_open_folder: "Apri Cartella",
    onb_submit: "Salva e Sincronizza"
  },
  fr: {
    dash_title: "PradoOS — Configuration UGR",
    onb_email: "Courriel Institutionnel UGR",
    onb_portal: "Portail PRADO",
    onb_password: "Mot de passe PRADO (SSO)",
    keychain_hint: "🔒 Stocké dans le Trousseau natif",
    onb_folder: "Dossier Local des Cours",
    btn_browse: "Parcourir...",
    lbl_preset_mode: "Organisation des Dossiers",
    lbl_fwd_enable: "Rediriger les courriels des professeurs (@correo.ugr.es) vers mon courriel :",
    lbl_notif_title: "Notifications du bureau",
    btn_open_folder: "Ouvrir Dossier",
    onb_submit: "Enregistrer et Synchroniser"
  }
};

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str == null ? "" : String(str);
  return d.innerHTML;
}

function showToast(msg) {
  const el = document.getElementById("toastBox");
  el.textContent = msg;
  el.classList.add("visible");
  setTimeout(() => el.classList.remove("visible"), 3500);
}

async function apiGet(path) {
  const res = await fetch(path, { headers: { "X-Prado-Token": PRADO_TOKEN } });
  return await res.json();
}

async function apiPost(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Prado-Token": PRADO_TOKEN
    },
    body: JSON.stringify(body)
  });
  return await res.json();
}

function applyTranslations(lang) {
  currentLang = I18N[lang] ? lang : "es";
  const dict = I18N[currentLang];
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const k = el.getAttribute("data-i18n");
    if (dict[k]) el.textContent = dict[k];
  });
  ["es", "en", "it", "fr"].forEach(code => {
    const b = document.getElementById("lang-" + code);
    if (b) b.classList.toggle("active", code === currentLang);
  });
}

async function setLanguage(lang) {
  applyTranslations(lang);
  await apiPost("/api/language", { language: lang });
}

function switchTab(tab) {
  ["dashboard", "courses", "mail", "calendar"].forEach(t => {
    const el = document.getElementById("view-" + t);
    if (el) el.classList.toggle("active", t === tab);
  });
  if (tab === "mail") {
    loadMailInbox(false);
  }
}

function openOnboardingModal() {
  document.getElementById("onboardingModal").classList.add("visible");
}

function closeOnboardingModal() {
  document.getElementById("onboardingModal").classList.remove("visible");
}

async function loadMailInbox(refresh) {
  const res = await apiGet(`/api/mail/messages?filter=all&refresh=${refresh ? "1" : "0"}`);
  if (res.status === "success") {
    const pane = document.getElementById("mailListPane");
    if (pane) {
      pane.innerHTML = (res.messages || []).map(m => `<div>${esc(m.sender)} ${esc(m.subject)}</div>`).join("");
    }
  }
}

async function pickFolderFor(inputId) {
  const res = await apiPost("/api/folder/pick", {});
  if (res.status === "success" && res.path) {
    document.getElementById(inputId).value = res.path;
  }
}

async function openCoursesFolder() {
  await apiPost("/api/folder/open", {});
}

async function submitCompactSetup() {
  const username = document.getElementById("onbUsername").value.trim();
  const password = document.getElementById("onbPassword").value;
  const portal = document.getElementById("onbPortal").value;
  const coursesRoot = document.getElementById("onbCoursesRoot").value.trim();
  const preset = document.getElementById("onbPreset").value;
  const notif = document.getElementById("onbNotifications").checked;
  const fwdEnabled = document.getElementById("cfgFwdEnabled").checked;
  const fwdTo = document.getElementById("cfgFwdTo").value.trim();

  await apiPost("/api/mail/forwarding", {
    forward_enabled: fwdEnabled,
    forward_to: fwdTo,
    forward_mode: "academic"
  });

  const res = await apiPost("/api/onboard", {
    language: currentLang,
    portal: portal,
    username: username,
    password: password,
    courses_root: coursesRoot,
    preset: preset,
    notifications_enabled: notif,
    start_sync: true
  });

  if (res.status === "success") {
    showToast("🚀 Configuración guardada. Sincronizando asignaturas en segundo plano...");
    refreshState();
  } else {
    showToast(`❌ ${res.error || "Error al guardar la configuración"}`);
  }
}

async function submitMfaCode() {
  const code = document.getElementById("mfaCodeInput").value.trim();
  const res = await apiPost("/api/auth/mfa", { code: code });
  if (res.status === "success") {
    document.getElementById("mfaCodeInput").value = "";
    document.getElementById("mfaModal").classList.remove("visible");
    showToast("✓ Código MFA enviado. Dispositivo verificado por 30 días.");
    refreshState();
  } else {
    showToast(`❌ ${res.error}`);
  }
}

async function refreshState() {
  try {
    const st = await apiGet("/api/state");
    appState = st;

    if (!formInitialized) {
      formInitialized = true;
      applyTranslations(st.language || "es");
      document.getElementById("onbPortal").value = st.auth.portal || "grado";
      document.getElementById("onbUsername").value = st.auth.username || "";
      document.getElementById("onbCoursesRoot").value = st.config.courses_root || "";
      document.getElementById("onbPreset").value = st.config.preset || "mirror";
      document.getElementById("onbNotifications").checked = Boolean(st.config.notifications_enabled);
      document.getElementById("cfgFwdEnabled").checked = Boolean(st.config.mail.forward_enabled);
      document.getElementById("cfgFwdTo").value = st.config.mail.forward_to || "";
    }

    document.getElementById("versionLabel").textContent = `v${st.version} • Barra de Menús / System Tray`;
    document.getElementById("sidebarUser").textContent = st.auth.username
      ? `🟢 ${st.auth.username} (${st.stats.active_courses} asignaturas)`
      : "🔴 Cuenta UGR pendiente de configurar";
    document.getElementById("lastSyncLabel").textContent = `Última sinc.: ${st.sync.last_sync_time || "--:--"}`;

    // Update hidden compatibility metrics
    document.getElementById("kpiCourses").textContent = `${st.stats.active_courses}/${st.stats.total_courses}`;
    document.getElementById("kpiFiles").textContent = st.stats.total_files;
    document.getElementById("kpiProtected").textContent = st.stats.protected_files;
    document.getElementById("kpiDeadlines").textContent = st.deadlines.length;
    const cl = document.getElementById("coursesManageList");
    if (cl) cl.innerHTML = (st.courses || []).map(c => `<div>${esc(c.fullname)}</div>`).join("");

    const badge = document.getElementById("syncStatusBadge");
    const progWrap = document.getElementById("syncProgressWrap");
    const progBar = document.getElementById("syncProgressBar");
    const btnSync = document.getElementById("btnSyncNow");

    if (st.sync.status === "syncing" || st.sync.status === "mfa_required") {
      badge.className = "badge badge-syncing";
      badge.textContent = "🟡 Sincronizando...";
      progWrap.classList.add("visible");
      progBar.style.width = `${st.sync.progress_pct || 15}%`;
      document.getElementById("syncStepText").textContent = st.sync.current_step || "Sincronizando con PRADO UGR...";
      btnSync.disabled = true;
    } else if (st.sync.status === "error") {
      badge.className = "badge badge-error";
      badge.textContent = "🔴 Error";
      progWrap.classList.remove("visible");
      btnSync.disabled = false;
    } else {
      badge.className = "badge badge-idle";
      badge.textContent = `🟢 Al día (${st.stats.total_files} archivos)`;
      progWrap.classList.remove("visible");
      btnSync.disabled = false;
    }

    const mfaModal = document.getElementById("mfaModal");
    if (st.sync.mfa_pending) {
      document.getElementById("mfaPromptText").textContent = st.sync.mfa_prompt || "Introduce el código de 6 dígitos enviado a @correo.ugr.es:";
      mfaModal.classList.add("visible");
    } else {
      mfaModal.classList.remove("visible");
    }
  } catch (e) {}
}

refreshState();
setInterval(refreshState, 1500);
</script>
</body>
</html>
"""
