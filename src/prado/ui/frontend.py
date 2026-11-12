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
  .badge-neutral { background: rgba(156, 163, 175, 0.14); color: var(--text-muted); }
  .badge-syncing { background: var(--amber-soft); color: var(--amber); }
  .badge-error { background: var(--red-soft); color: var(--red); }
  .input-error { border-color: var(--red) !important; }
  .field-error {
    display: none;
    font-size: 11.5px;
    color: var(--red);
    margin-top: 2px;
    font-weight: 500;
  }
  .field-error.visible { display: block; }
  .form-error-banner {
    display: none;
    padding: 9px 12px;
    border-radius: 8px;
    background: var(--red-soft);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: var(--red);
    font-size: 12px;
    font-weight: 500;
  }
  .form-error-banner.visible { display: block; }
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
      <span id="sidebarUser" style="font-weight:600;" data-i18n="status_unconfigured">⚪ Cuenta UGR pendiente de configurar</span>
      <span class="badge badge-neutral" id="syncStatusBadge" data-i18n="badge_setup_pending">⚪ Pendiente de configurar</span>
    </div>

    <!-- 1. UGR Credentials & Portal -->
    <div class="grid-2">
      <div class="form-group">
        <label class="form-label" data-i18n="onb_email">Correo Institucional UGR</label>
        <input type="email" class="input" id="onbUsername" placeholder="usuario@correo.ugr.es" data-i18n-placeholder="ph_email" oninput="clearFieldError('onbUsername')">
        <div class="field-error" id="err-username"></div>
      </div>
      <div class="form-group">
        <label class="form-label" data-i18n="onb_portal">Portal PRADO</label>
        <select class="select" id="onbPortal">
          <option value="grado" data-i18n="opt_portal_grado">Grado (pradogrado)</option>
          <option value="posgrado" data-i18n="opt_portal_posgrado">Posgrado / Máster</option>
          <option value="ceprud" data-i18n="opt_portal_ceprud">CEPRUD / Otros</option>
        </select>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">
        <span data-i18n="onb_password">Contraseña PRADO (Acceso Identificado)</span>
        <span class="form-hint" data-i18n="keychain_hint">🔒 Guardada en Llavero nativo</span>
      </label>
      <input type="password" class="input" id="onbPassword" placeholder="••••••••••••••••" oninput="clearFieldError('onbPassword')">
      <div class="field-error" id="err-password"></div>
    </div>

    <!-- 2. Destination Folder & Organization Mode -->
    <div class="form-group">
      <label class="form-label" data-i18n="onb_folder">Carpeta Local de Apuntes</label>
      <div class="row">
        <input type="text" class="input" id="onbCoursesRoot" placeholder="~/Documents/UGR_Courses" oninput="clearFieldError('onbCoursesRoot')">
        <button class="btn btn-secondary" onclick="pickFolderFor('onbCoursesRoot')">📂 <span data-i18n="btn_browse">Elegir...</span></button>
      </div>
      <div class="field-error" id="err-courses_root"></div>
    </div>

    <div class="form-group">
      <label class="form-label" data-i18n="lbl_preset_mode">Organización de Carpetas</label>
      <select class="select" id="onbPreset">
        <option value="mirror" data-i18n="opt_preset_mirror">Mirror — Estructura oficial de cada profesor en PRADO</option>
        <option value="smart" data-i18n="opt_preset_smart">Smart — Separar automáticamente Teoría / Prácticas / General</option>
      </select>
    </div>

    <!-- 3. Optional Mail Auto-Forwarding & Background Preferences -->
    <div class="section-box">
      <label class="check-row">
        <input type="checkbox" id="cfgFwdEnabled">
        <span data-i18n="lbl_fwd_enable">Reenviar correos de profesores (@correo.ugr.es) a mi correo personal:</span>
      </label>
      <input type="email" class="input" id="cfgFwdTo" placeholder="tu.correo@gmail.com" data-i18n-placeholder="ph_fwd_email">

      <div class="row" style="justify-content:space-between; padding-top:4px;">
        <label class="check-row">
          <input type="checkbox" id="onbNotifications" checked>
          <span data-i18n="lbl_notif_title">Notificaciones de escritorio</span>
        </label>
        <span style="font-size:11.5px; color:var(--text-muted);" id="lastSyncLabel">Última sinc.: --:--</span>
      </div>
    </div>

    <div class="form-error-banner" id="formErrorBanner"></div>

    <!-- Inline Progress Bar (visible during sync) -->
    <div class="progress-wrap" id="syncProgressWrap">
      <div style="display:flex; justify-content:space-between; font-size:12px;">
        <span id="syncStepText" data-i18n="sync_in_progress">Sincronizando con PRADO UGR...</span>
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
      <div style="font-size:16px; font-weight:700; margin-bottom:8px;" data-i18n="mfa_title">🔐 Verificación en 2 Pasos (MFA UGR)</div>
      <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:14px;" id="mfaPromptText" data-i18n="mfa_prompt_default">
        Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es. Tu dispositivo quedará verificado por 30 días.
      </p>
      <div class="form-group">
        <input type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" class="input" id="mfaCodeInput" placeholder="123456" style="font-size:22px; text-align:center; letter-spacing:8px; font-weight:700;">
        <div class="field-error" id="err-mfa"></div>
      </div>
      <div class="row" style="margin-top:14px;">
        <button class="btn btn-primary" onclick="submitMfaCode()" style="width:100%;" data-i18n="mfa_verify_btn">✓ Verificar Dispositivo (30 días)</button>
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
    subtitle_tray: "Barra de Menús / Bandeja del Sistema",
    status_unconfigured: "⚪ Cuenta UGR pendiente de configurar",
    badge_setup_pending: "⚪ Pendiente de configurar",
    badge_idle: "🟢 Al día",
    badge_syncing: "🟡 Sincronizando...",
    badge_error: "🔴 Error",
    courses_unit: "asignaturas",
    files_unit: "archivos",
    last_sync_prefix: "Última sinc.:",
    onb_email: "Correo Institucional UGR",
    ph_email: "usuario@correo.ugr.es",
    onb_portal: "Portal PRADO",
    opt_portal_grado: "Grado (pradogrado)",
    opt_portal_posgrado: "Posgrado / Máster",
    opt_portal_ceprud: "CEPRUD / Otros",
    onb_password: "Contraseña PRADO (Acceso Identificado)",
    keychain_hint: "🔒 Guardada en Llavero nativo",
    onb_folder: "Carpeta Local de Apuntes",
    btn_browse: "Elegir...",
    lbl_preset_mode: "Organización de Carpetas",
    opt_preset_mirror: "Mirror — Estructura oficial de cada profesor en PRADO",
    opt_preset_smart: "Smart — Separar automáticamente Teoría / Prácticas / General",
    lbl_fwd_enable: "Reenviar correos de profesores (@correo.ugr.es) a mi correo personal:",
    ph_fwd_email: "tu.correo@gmail.com",
    lbl_notif_title: "Notificaciones de escritorio",
    sync_in_progress: "Sincronizando con PRADO UGR...",
    btn_open_folder: "Abrir Carpeta",
    onb_submit: "Guardar y Sincronizar",
    toast_saved_syncing: "🚀 Configuración guardada. Sincronizando asignaturas...",
    toast_save_error: "Error al guardar la configuración",
    mfa_title: "🔐 Verificación en 2 Pasos (MFA UGR)",
    mfa_prompt_default: "Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es. Tu dispositivo quedará verificado por 30 días.",
    mfa_verify_btn: "✓ Verificar Dispositivo (30 días)",
    toast_mfa_ok: "✓ Código MFA enviado. Dispositivo verificado por 30 días."
  },
  en: {
    dash_title: "PradoOS — UGR Setup",
    subtitle_tray: "Menu Bar / System Tray",
    status_unconfigured: "⚪ UGR account setup pending",
    badge_setup_pending: "⚪ Setup required",
    badge_idle: "🟢 Up to date",
    badge_syncing: "🟡 Syncing...",
    badge_error: "🔴 Error",
    courses_unit: "courses",
    files_unit: "files",
    last_sync_prefix: "Last sync:",
    onb_email: "UGR Institutional Email",
    ph_email: "username@correo.ugr.es",
    onb_portal: "PRADO Portal",
    opt_portal_grado: "Undergraduate (pradogrado)",
    opt_portal_posgrado: "Postgraduate / Master's",
    opt_portal_ceprud: "CEPRUD / Other",
    onb_password: "PRADO Password (SSO)",
    keychain_hint: "🔒 Stored in OS Keychain",
    onb_folder: "Local Courses Folder",
    btn_browse: "Browse...",
    lbl_preset_mode: "Folder Organization",
    opt_preset_mirror: "Mirror — Official PRADO structure per course",
    opt_preset_smart: "Smart — Auto-split Theory / Labs / General",
    lbl_fwd_enable: "Auto-forward professor emails (@correo.ugr.es) to my personal email:",
    ph_fwd_email: "your.email@gmail.com",
    lbl_notif_title: "Desktop notifications",
    sync_in_progress: "Syncing with PRADO UGR...",
    btn_open_folder: "Open Folder",
    onb_submit: "Save & Sync Now",
    toast_saved_syncing: "🚀 Settings saved. Syncing your courses...",
    toast_save_error: "Could not save settings",
    mfa_title: "🔐 2-Step Verification (UGR MFA)",
    mfa_prompt_default: "Enter the 6-digit code sent to your @correo.ugr.es inbox. Your device stays trusted for 30 days.",
    mfa_verify_btn: "✓ Verify Device (30 days)",
    toast_mfa_ok: "✓ MFA code submitted. Device trusted for 30 days."
  },
  it: {
    dash_title: "PradoOS — Configurazione UGR",
    subtitle_tray: "Barra dei Menu / System Tray",
    status_unconfigured: "⚪ Account UGR da configurare",
    badge_setup_pending: "⚪ Da configurare",
    badge_idle: "🟢 Aggiornato",
    badge_syncing: "🟡 Sincronizzazione...",
    badge_error: "🔴 Errore",
    courses_unit: "corsi",
    files_unit: "file",
    last_sync_prefix: "Ultima sinc.:",
    onb_email: "Email Istituzionale UGR",
    ph_email: "utente@correo.ugr.es",
    onb_portal: "Portale PRADO",
    opt_portal_grado: "Laurea Triennale (pradogrado)",
    opt_portal_posgrado: "Magistrale / Master",
    opt_portal_ceprud: "CEPRUD / Altri",
    onb_password: "Password PRADO (SSO)",
    keychain_hint: "🔒 Salvata nel Portachiavi nativo",
    onb_folder: "Cartella Locale Appunti",
    btn_browse: "Sfoglia...",
    lbl_preset_mode: "Organizzazione Cartelle",
    opt_preset_mirror: "Mirror — Struttura ufficiale di ogni docente su PRADO",
    opt_preset_smart: "Smart — Separa automaticamente Teoria / Pratiche / Generale",
    lbl_fwd_enable: "Inoltra email dei docenti (@correo.ugr.es) alla mia email personale:",
    ph_fwd_email: "tua.email@gmail.com",
    lbl_notif_title: "Notifiche desktop",
    sync_in_progress: "Sincronizzazione con PRADO UGR...",
    btn_open_folder: "Apri Cartella",
    onb_submit: "Salva e Sincronizza",
    toast_saved_syncing: "🚀 Configurazione salvata. Sincronizzazione avviata...",
    toast_save_error: "Impossibile salvare la configurazione",
    mfa_title: "🔐 Verifica in 2 Passaggi (MFA UGR)",
    mfa_prompt_default: "Inserisci il codice a 6 cifre inviato alla tua email @correo.ugr.es. Il dispositivo resterà verificato per 30 giorni.",
    mfa_verify_btn: "✓ Verifica Dispositivo (30 giorni)",
    toast_mfa_ok: "✓ Codice MFA inviato. Dispositivo verificato per 30 giorni."
  },
  fr: {
    dash_title: "PradoOS — Configuration UGR",
    subtitle_tray: "Barre des Menus / Zone de Notification",
    status_unconfigured: "⚪ Compte UGR à configurer",
    badge_setup_pending: "⚪ À configurer",
    badge_idle: "🟢 À jour",
    badge_syncing: "🟡 Synchronisation...",
    badge_error: "🔴 Erreur",
    courses_unit: "cours",
    files_unit: "fichiers",
    last_sync_prefix: "Dernière sync :",
    onb_email: "Courriel Institutionnel UGR",
    ph_email: "utilisateur@correo.ugr.es",
    onb_portal: "Portail PRADO",
    opt_portal_grado: "Licence / Grado (pradogrado)",
    opt_portal_posgrado: "Master / Posgrado",
    opt_portal_ceprud: "CEPRUD / Autres",
    onb_password: "Mot de passe PRADO (SSO)",
    keychain_hint: "🔒 Stocké dans le Trousseau natif",
    onb_folder: "Dossier Local des Cours",
    btn_browse: "Parcourir...",
    lbl_preset_mode: "Organisation des Dossiers",
    opt_preset_mirror: "Mirror — Structure officielle PRADO de chaque cours",
    opt_preset_smart: "Smart — Séparer Théorie / TP / Général",
    lbl_fwd_enable: "Rediriger les courriels des professeurs (@correo.ugr.es) vers mon courriel :",
    ph_fwd_email: "votre.email@gmail.com",
    lbl_notif_title: "Notifications du bureau",
    sync_in_progress: "Synchronisation avec PRADO UGR...",
    btn_open_folder: "Ouvrir Dossier",
    onb_submit: "Enregistrer et Synchroniser",
    toast_saved_syncing: "🚀 Configuration enregistrée. Synchronisation en cours...",
    toast_save_error: "Erreur lors de l'enregistrement",
    mfa_title: "🔐 Validation en 2 Étapes (MFA UGR)",
    mfa_prompt_default: "Saisissez le code à 6 chiffres envoyé à @correo.ugr.es. Votre appareil restera approuvé pendant 30 jours.",
    mfa_verify_btn: "✓ Approuver l'Appareil (30 jours)",
    toast_mfa_ok: "✓ Code MFA envoyé. Appareil approuvé pour 30 jours."
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
  document.documentElement.lang = currentLang;
  document.title = dict.dash_title;
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const k = el.getAttribute("data-i18n");
    if (dict[k]) el.textContent = dict[k];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const k = el.getAttribute("data-i18n-placeholder");
    if (dict[k]) el.setAttribute("placeholder", dict[k]);
  });
  ["es", "en", "it", "fr"].forEach(code => {
    const b = document.getElementById("lang-" + code);
    if (b) b.classList.toggle("active", code === currentLang);
  });
  if (appState) renderStateText(appState);
}

function clearFieldError(inputId) {
  const input = document.getElementById(inputId);
  if (input) input.classList.remove("input-error");
  const fieldMap = { onbUsername: "err-username", onbPassword: "err-password", onbCoursesRoot: "err-courses_root" };
  const errEl = document.getElementById(fieldMap[inputId] || "");
  if (errEl) {
    errEl.textContent = "";
    errEl.classList.remove("visible");
  }
  const banner = document.getElementById("formErrorBanner");
  if (banner) {
    banner.textContent = "";
    banner.classList.remove("visible");
  }
}

function clearAllErrors() {
  ["onbUsername", "onbPassword", "onbCoursesRoot"].forEach(clearFieldError);
}

function showFieldError(field, message) {
  const inputMap = { username: "onbUsername", password: "onbPassword", courses_root: "onbCoursesRoot" };
  const inputId = inputMap[field];
  const errEl = document.getElementById("err-" + field);
  if (inputId && errEl) {
    const inp = document.getElementById(inputId);
    if (inp) {
      inp.classList.add("input-error");
      inp.focus();
    }
    errEl.textContent = message;
    errEl.classList.add("visible");
  } else {
    const banner = document.getElementById("formErrorBanner");
    if (banner) {
      banner.textContent = message;
      banner.classList.add("visible");
    }
  }
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
  clearAllErrors();
  const dict = I18N[currentLang] || I18N.es;
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
    showToast(dict.toast_saved_syncing);
    refreshState();
  } else {
    const msg = res.error || dict.toast_save_error;
    showFieldError(res.field || "", msg);
    showToast(`❌ ${msg}`);
  }
}

async function submitMfaCode() {
  const dict = I18N[currentLang] || I18N.es;
  const code = document.getElementById("mfaCodeInput").value.trim();
  const errMfa = document.getElementById("err-mfa");
  if (errMfa) { errMfa.textContent = ""; errMfa.classList.remove("visible"); }
  const res = await apiPost("/api/auth/mfa", { code: code });
  if (res.status === "success") {
    document.getElementById("mfaCodeInput").value = "";
    document.getElementById("mfaModal").classList.remove("visible");
    showToast(dict.toast_mfa_ok);
    refreshState();
  } else {
    if (errMfa) {
      errMfa.textContent = res.error;
      errMfa.classList.add("visible");
    }
    showToast(`❌ ${res.error}`);
  }
}

function renderStateText(st) {
  const dict = I18N[currentLang] || I18N.es;
  const isConfigured = Boolean(st.is_onboarded || st.auth.username);
  document.getElementById("versionLabel").textContent = `v${st.version} • ${dict.subtitle_tray}`;
  document.getElementById("sidebarUser").textContent = st.auth.username
    ? `🟢 ${st.auth.username} (${st.stats.active_courses} ${dict.courses_unit})`
    : dict.status_unconfigured;
  document.getElementById("lastSyncLabel").textContent = `${dict.last_sync_prefix} ${st.sync.last_sync_time || "--:--"}`;

  const badge = document.getElementById("syncStatusBadge");
  const progWrap = document.getElementById("syncProgressWrap");
  const progBar = document.getElementById("syncProgressBar");
  const btnSync = document.getElementById("btnSyncNow");

  if (st.sync.status === "syncing" || st.sync.status === "mfa_required") {
    badge.className = "badge badge-syncing";
    badge.textContent = dict.badge_syncing;
    progWrap.classList.add("visible");
    progBar.style.width = `${st.sync.progress_pct || 15}%`;
    document.getElementById("syncStepText").textContent = st.sync.current_step || dict.sync_in_progress;
    btnSync.disabled = true;
  } else if (st.sync.status === "error") {
    badge.className = "badge badge-error";
    badge.textContent = dict.badge_error;
    progWrap.classList.remove("visible");
    btnSync.disabled = false;
  } else if (!isConfigured) {
    badge.className = "badge badge-neutral";
    badge.textContent = dict.badge_setup_pending;
    progWrap.classList.remove("visible");
    btnSync.disabled = false;
  } else {
    badge.className = "badge badge-idle";
    badge.textContent = `${dict.badge_idle} (${st.stats.total_files} ${dict.files_unit})`;
    progWrap.classList.remove("visible");
    btnSync.disabled = false;
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

    renderStateText(st);

    // Update hidden compatibility metrics
    document.getElementById("kpiCourses").textContent = `${st.stats.active_courses}/${st.stats.total_courses}`;
    document.getElementById("kpiFiles").textContent = st.stats.total_files;
    document.getElementById("kpiProtected").textContent = st.stats.protected_files;
    document.getElementById("kpiDeadlines").textContent = st.deadlines.length;
    const cl = document.getElementById("coursesManageList");
    if (cl) cl.innerHTML = (st.courses || []).map(c => `<div>${esc(c.fullname)}</div>`).join("");

    const mfaModal = document.getElementById("mfaModal");
    if (st.sync.mfa_pending) {
      const dict = I18N[currentLang] || I18N.es;
      document.getElementById("mfaPromptText").textContent = st.sync.mfa_prompt || dict.mfa_prompt_default;
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
