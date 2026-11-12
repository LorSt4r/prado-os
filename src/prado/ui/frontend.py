"""
PradoOS Compact Setup & Quick-Configure Window (Single-Screen Native Card).

Designed following Maestral, Tailscale, and Obsidian desktop UI patterns:
- Daily actions live in the OS Menu Bar / System Tray with focused submenus.
- This compact 2-tab Setup Card (525x640px) handles account connection,
  local folder & Mirror/Smart organization, Mail forwarding, and 2FA MFA prompts.
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
    /* Palette 1: Academic Slate + UGR Crimson (Dark default) */
    --bg-app: #0f1117;
    --bg-card: #171a23;
    --bg-surface: #131620;
    --bg-input: #1f2430;
    --border: #2b3140;
    --text-main: #f1f4f9;
    --text-muted: #9aa3b2;
    --accent: #e11d48;
    --accent-hover: #be123c;
    --accent-soft: rgba(225, 29, 72, 0.14);
    --green: #34d399;
    --green-soft: rgba(16, 185, 129, 0.14);
    --amber: #fbbf24;
    --amber-soft: rgba(245, 158, 11, 0.14);
    --red: #f87171;
    --red-soft: rgba(239, 68, 68, 0.14);
    --radius: 12px;
  }
  @media (prefers-color-scheme: light) {
    :root {
      /* Palette 1: Academic Slate + UGR Crimson (Light mode) */
      --bg-app: #f8fafc;
      --bg-card: #ffffff;
      --bg-surface: #f1f5f9;
      --bg-input: #ffffff;
      --border: #dbe2ea;
      --text-main: #0f172a;
      --text-muted: #475569;
      --accent: #c8102e;
      --accent-hover: #9f1239;
      --accent-soft: rgba(200, 16, 46, 0.10);
      --green: #047857;
      --green-soft: rgba(5, 150, 105, 0.12);
      --amber: #b45309;
      --amber-soft: rgba(217, 119, 6, 0.12);
      --red: #dc2626;
      --red-soft: rgba(220, 38, 38, 0.10);
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
    padding: 12px;
    user-select: none;
    -webkit-font-smoothing: antialiased;
  }
  .setup-card {
    width: 100%;
    max-width: 492px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px 20px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }
  .brand-logo {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--accent-hover));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
  }
  .brand-title { font-size: 15px; font-weight: 700; letter-spacing: -0.01em; line-height: 1.25; }
  .brand-sub { font-size: 12px; color: var(--text-muted); margin-top: 1px; }
  .lang-row { display: flex; gap: 4px; flex-shrink: 0; }
  .lang-btn {
    border: 1px solid var(--border);
    background: var(--bg-surface);
    color: var(--text-muted);
    font-size: 12px;
    font-weight: 600;
    padding: 5px 8px;
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .lang-btn:hover { color: var(--text-main); border-color: var(--accent); }
  .lang-btn.active { background: var(--accent); color: #ffffff; border-color: var(--accent); }

  /* Card Navigation Tabs */
  .card-tabs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 3px;
  }
  .card-tab {
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    font-size: 13px;
    font-weight: 500;
    padding: 8px 10px;
    border-radius: 7px;
    cursor: pointer;
  }
  .card-tab:hover { color: var(--text-main); }
  .card-tab.active {
    background: var(--bg-card);
    color: var(--text-main);
    font-weight: 700;
    border-color: var(--accent);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.14);
  }
  .tab-panel { display: none; flex-direction: column; gap: 10px; }
  .tab-panel.active { display: flex; }

  .status-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 7px 12px;
    font-size: 12.5px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }
  .badge-neutral { background: rgba(148, 163, 184, 0.16); color: var(--text-muted); }
  .badge-idle { background: var(--green-soft); color: var(--green); }
  .badge-syncing { background: var(--amber-soft); color: var(--amber); }
  .badge-error { background: var(--red-soft); color: var(--red); }

  /* Unified Connected Account Card */
  .account-card {
    display: none;
    flex-direction: column;
    gap: 8px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 11px 13px;
  }
  .account-card.visible { display: flex; }
  .account-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .account-meta { min-width: 0; }
  .account-email { font-size: 13.5px; font-weight: 700; color: var(--text-main); word-break: break-all; }
  .account-sub { font-size: 12px; color: var(--text-muted); }
  .link-btn {
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--accent);
    font-size: 12px;
    font-weight: 600;
    padding: 6px 10px;
    border-radius: 8px;
    cursor: pointer;
    white-space: nowrap;
  }
  .link-btn:hover { border-color: var(--accent); background: var(--accent-soft); }

  .creds-wrap { display: flex; flex-direction: column; gap: 9px; }
  .creds-wrap.collapsed { display: none; }

  .grid-2 { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 10px; }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .form-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .form-hint { font-size: 12px; color: var(--green); font-weight: 500; }
  .input-wrap { position: relative; display: flex; align-items: center; width: 100%; }
  .input, .select {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-main);
    border-radius: 9px;
    padding: 8px 11px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s ease;
  }
  .input-pw { padding-right: 40px; }
  .input:focus, .select:focus { border-color: var(--accent); }
  .input.input-error { border-color: var(--red); background: var(--red-soft); }
  .pw-toggle {
    position: absolute;
    right: 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    padding: 5px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
  }
  .pw-toggle:hover { color: var(--text-main); }

  .field-error {
    display: none;
    font-size: 12px;
    color: var(--red);
    font-weight: 500;
    margin-top: 2px;
  }
  .field-error.visible { display: block; }
  .form-error-banner {
    display: none;
    background: var(--red-soft);
    border: 1px solid rgba(220, 38, 38, 0.35);
    color: var(--red);
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 12.5px;
    font-weight: 500;
  }
  .form-error-banner.visible { display: block; }

  .row { display: flex; gap: 8px; align-items: center; }
  .btn {
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 9px 15px;
    font-size: 13px;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    white-space: nowrap;
  }
  .btn:disabled { opacity: 0.55; cursor: not-allowed; }
  .btn-primary { background: var(--accent); color: #ffffff; }
  .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
  .btn-secondary { background: var(--bg-surface); color: var(--text-main); border-color: var(--border); }
  .btn-secondary:hover:not(:disabled) { border-color: var(--text-muted); }
  .btn-danger-ghost { background: transparent; color: var(--red); border-color: var(--border); }
  .btn-danger-ghost:hover:not(:disabled) { background: var(--red-soft); border-color: rgba(220, 38, 38, 0.4); }

  /* Segmented Mirror vs Smart + Live Tree Preview */
  .seg-control {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 3px;
  }
  .seg-btn {
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    padding: 7px 10px;
    border-radius: 7px;
    font-size: 12.5px;
    font-weight: 500;
    cursor: pointer;
  }
  .seg-btn.active {
    background: var(--accent-soft);
    color: var(--text-main);
    font-weight: 700;
    border-color: var(--accent);
  }
  .tree-preview {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 11px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    line-height: 1.42;
    color: var(--text-muted);
  }
  .tree-desc {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    font-size: 12px;
    color: var(--text-main);
    font-weight: 500;
    margin-bottom: 4px;
  }

  .section-box {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .check-row {
    display: flex;
    align-items: flex-start;
    gap: 9px;
    font-size: 13px;
    color: var(--text-main);
    cursor: pointer;
    line-height: 1.35;
  }
  .check-row input[type="checkbox"] { width: 16px; height: 16px; margin-top: 2px; accent-color: var(--accent); cursor: pointer; flex-shrink: 0; }
  .helper-text { font-size: 12px; color: var(--text-muted); line-height: 1.4; }

  .progress-wrap {
    display: none;
    flex-direction: column;
    gap: 6px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
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
    background: linear-gradient(90deg, var(--accent), #f59e0b);
    width: 0%;
    transition: width 0.25s ease;
  }
  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }

  /* MFA 6-digit modal overlay */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.72);
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
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
  }
  .modal-actions {
    display: grid;
    grid-template-columns: 0.9fr 1.4fr;
    gap: 8px;
    margin-top: 14px;
  }
  .doctor-list {
    max-height: 290px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 7px;
    margin-top: 10px;
  }
  .doctor-row {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 8px 10px;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
  }
  .doctor-pill {
    font-size: 10.5px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 999px;
    flex-shrink: 0;
  }
  .doctor-pill.ok { background: var(--green-soft); color: var(--green); }
  .doctor-pill.warn { background: var(--amber-soft); color: var(--amber); }
  .doctor-pill.fail { background: var(--red-soft); color: var(--red); }
  .toast {
    position: fixed;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    background: #0f172a;
    color: #ffffff;
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

  <div class="setup-card" id="onboardingModal">
    <!-- Header -->
    <div class="header">
      <div class="brand">
        <div class="brand-logo" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
        </div>
        <div>
          <div class="brand-title" data-i18n="dash_title">PradoOS — Configuración UGR</div>
          <div class="brand-sub" id="versionLabel">Barra de Menús / System Tray</div>
        </div>
      </div>
      <div class="lang-row">
        <button class="lang-btn active" id="lang-es" onclick="setLanguage('es')">ES</button>
        <button class="lang-btn" id="lang-en" onclick="setLanguage('en')">EN</button>
        <button class="lang-btn" id="lang-it" onclick="setLanguage('it')">IT</button>
        <button class="lang-btn" id="lang-fr" onclick="setLanguage('fr')">FR</button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="card-tabs" role="tablist">
      <button type="button" class="card-tab active" id="tabBtnAccount" onclick="switchCardTab('account')" data-i18n="tab_account">Cuenta y Carpeta</button>
      <button type="button" class="card-tab" id="tabBtnPrefs" onclick="switchCardTab('prefs')" data-i18n="tab_prefs">Correo y Opciones</button>
    </div>

    <!-- Live Status Pill (shown when unconfigured or on Preferences tab) -->
    <div class="status-strip" id="unconfiguredStrip">
      <span id="sidebarUser" style="font-weight:600;" data-i18n="status_unconfigured">Cuenta UGR pendiente de configurar</span>
      <span class="badge badge-neutral" id="syncStatusBadge" data-i18n="badge_setup_pending">Pendiente de configurar</span>
    </div>

    <!-- TAB 1: ACCOUNT & FOLDER -->
    <div class="tab-panel active" id="cardTabAccount">
      <!-- Unified Connected Summary (replaces status-strip + credentials form when connected) -->
      <div class="account-card" id="connectedSummaryCard">
        <div class="account-row">
          <div class="account-email" id="connectedUserText">estudiante@correo.ugr.es</div>
          <span class="badge badge-idle" id="syncStatusBadgeConn">Al día</span>
        </div>
        <div class="account-row">
          <div class="account-sub" id="connectedSubText"></div>
          <button type="button" class="link-btn" id="btnToggleCreds" onclick="toggleCredentialsEditor(true)" data-i18n="btn_edit_creds">Cambiar contraseña</button>
        </div>
      </div>

      <!-- Editable Credentials Form (replaces connectedSummaryCard in-place when editing) -->
      <div class="creds-wrap" id="credentialsFieldsWrap">
        <div class="grid-2">
          <div class="form-group">
            <label class="form-label" for="onbUsername">
              <span data-i18n="onb_email">Correo Institucional UGR</span>
              <button type="button" class="link-btn" id="btnCancelCredsEdit" style="display:none; padding:2px 7px; font-size:11px;" onclick="toggleCredentialsEditor(false)" data-i18n="mfa_cancel_btn">Cancelar</button>
            </label>
            <input type="email" class="input" id="onbUsername" placeholder="usuario@correo.ugr.es" data-i18n-placeholder="ph_email" oninput="clearFieldError('onbUsername')">
            <div class="field-error" id="err-username"></div>
          </div>
          <div class="form-group">
            <label class="form-label" for="onbPortal" data-i18n="onb_portal">Portal PRADO</label>
            <select class="select" id="onbPortal">
              <option value="grado" data-i18n="opt_portal_grado">Grado (pradogrado)</option>
              <option value="posgrado" data-i18n="opt_portal_posgrado">Posgrado / Máster</option>
              <option value="ceprud" data-i18n="opt_portal_ceprud">CEPRUD / Otros</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="onbPassword">
            <span data-i18n="onb_password">Contraseña PRADO (Acceso Identificado)</span>
            <span class="form-hint" data-i18n="keychain_hint">Guardada en Llavero nativo</span>
          </label>
          <div class="input-wrap">
            <input type="password" class="input input-pw" id="onbPassword" placeholder="••••••••••••••••" oninput="clearFieldError('onbPassword')">
            <button type="button" class="pw-toggle" id="btnPwToggle" onclick="togglePasswordVisibility()" aria-label="Show password">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
          </div>
          <div class="field-error" id="err-password"></div>
        </div>
      </div>

      <!-- Folder Location -->
      <div class="form-group">
        <label class="form-label" for="onbCoursesRoot" data-i18n="onb_folder">Carpeta Local de Apuntes</label>
        <div class="row">
          <input type="text" class="input" id="onbCoursesRoot" placeholder="~/Documents/UGR_Courses" oninput="clearFieldError('onbCoursesRoot'); updateTreePreview();">
          <button type="button" class="btn btn-secondary" onclick="pickFolderFor('onbCoursesRoot')" data-i18n="btn_browse">Elegir...</button>
        </div>
        <div class="field-error" id="err-courses_root"></div>
      </div>

      <!-- Segmented Mirror / Smart + Live Tree Preview -->
      <div class="form-group">
        <label class="form-label" data-i18n="lbl_preset_mode">Organización de Carpetas</label>
        <select class="select" id="onbPreset" style="display:none;" onchange="setPresetMode(this.value)">
          <option value="mirror">Mirror</option>
          <option value="smart">Smart</option>
        </select>
        <div class="seg-control">
          <button type="button" class="seg-btn active" id="segMirror" onclick="setPresetMode('mirror')" data-i18n="seg_mirror">Mirror (PRADO oficial)</button>
          <button type="button" class="seg-btn" id="segSmart" onclick="setPresetMode('smart')" data-i18n="seg_smart">Smart (Teoría / Prácticas)</button>
        </div>
        <div class="tree-preview" id="treePreviewBox">
          <div class="tree-desc" id="treePreviewDesc"></div>
          <div id="treePreviewLines"></div>
        </div>
      </div>
    </div>

    <!-- TAB 2: MAIL & PREFERENCES -->
    <div class="tab-panel" id="cardTabPrefs">
      <div class="section-box">
        <label class="check-row">
          <input type="checkbox" id="cfgFwdEnabled">
          <span data-i18n="lbl_fwd_enable">Reenviar correos de profesores (@correo.ugr.es) a mi correo personal:</span>
        </label>
        <input type="email" class="input" id="cfgFwdTo" placeholder="tu.correo@gmail.com" data-i18n-placeholder="ph_fwd_email">
        <div class="helper-text" data-i18n="fwd_helper">Se filtra el correo académico de PRADO/profesores sin reenviar spam.</div>
      </div>

      <div class="section-box">
        <label class="check-row">
          <input type="checkbox" id="onbNotifications" checked onchange="toggleNotificationsImmediate(this.checked)">
          <span data-i18n="lbl_notif_title">Notificaciones de escritorio (nuevos apuntes y entregas)</span>
        </label>
        <label class="check-row">
          <input type="checkbox" id="onbAutostart" onchange="toggleAutostartImmediate(this.checked)">
          <span data-i18n="lbl_autostart">Abrir PradoOS al iniciar sesión</span>
        </label>
        <div class="form-group">
          <label class="form-label" for="onbAutoSyncSelect" data-i18n="lbl_autosync_freq">Sincronización automática en segundo plano</label>
          <select class="select" id="onbAutoSyncSelect">
            <option value="off" data-i18n="opt_autosync_off">Desactivada (solo manual desde la barra)</option>
            <option value="30" data-i18n="opt_autosync_30">Cada 30 minutos</option>
            <option value="60" data-i18n="opt_autosync_60">Cada 1 hora (Recomendado)</option>
            <option value="120" data-i18n="opt_autosync_120">Cada 2 horas</option>
          </select>
        </div>
      </div>

      <div class="section-box">
        <div class="row" style="justify-content:space-between;">
          <span class="helper-text" id="lastSyncLabel">Última sinc.: --:--</span>
          <div class="row">
            <button type="button" class="btn btn-secondary" style="padding:7px 12px; font-size:12px;" onclick="runQuickDoctor()" data-i18n="btn_run_doctor">Diagnóstico</button>
            <button type="button" class="btn btn-danger-ghost" id="btnLogoutQuick" style="padding:7px 12px; font-size:12px; display:none;" onclick="logoutAccount()" data-i18n="btn_logout">Cerrar sesión</button>
          </div>
        </div>
        <div class="helper-text" id="doctorQuickResult" style="display:none;"></div>
      </div>
    </div>

    <div class="form-error-banner" id="formErrorBanner"></div>

    <!-- Inline Progress Bar (visible during sync) -->
    <div class="progress-wrap" id="syncProgressWrap">
      <div style="display:flex; justify-content:space-between; font-size:12.5px;">
        <span id="syncStepText" data-i18n="sync_in_progress">Sincronizando con PRADO UGR...</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="syncProgressBar"></div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="footer">
      <button type="button" class="btn btn-secondary" onclick="openCoursesFolder()" data-i18n="btn_open_folder">Abrir Carpeta</button>
      <button type="button" class="btn btn-primary" onclick="submitCompactSetup()" id="btnSyncNow" data-i18n="onb_submit">Guardar y Sincronizar</button>
    </div>
  </div>

  <!-- LIVE 6-DIGIT MFA VERIFICATION MODAL -->
  <div class="modal-backdrop" id="mfaModal">
    <div class="modal-card">
      <div style="font-size:16px; font-weight:700; margin-bottom:8px;" data-i18n="mfa_title">Verificación en 2 Pasos (MFA UGR)</div>
      <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:12px;" id="mfaPromptText" data-i18n="mfa_prompt_default">
        Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es. Tu dispositivo quedará verificado por 30 días.
      </p>
      <div class="form-group">
        <input type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" class="input" id="mfaCodeInput" placeholder="123456" style="font-size:22px; text-align:center; letter-spacing:8px; font-weight:700;">
        <div class="field-error" id="err-mfa"></div>
      </div>
      <p class="helper-text" style="margin-top:8px;" data-i18n="mfa_help_hint">Si no llega en 30 segundos, revisa la carpeta de Correo no deseado en @correo.ugr.es.</p>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" id="btnMfaCancel" onclick="cancelMfaModal()" data-i18n="mfa_cancel_btn">Cancelar</button>
        <button type="button" class="btn btn-primary" id="btnMfaVerify" onclick="submitMfaCode()" data-i18n="mfa_verify_btn">Verificar (30 días)</button>
      </div>
    </div>
  </div>

  <!-- DOCTOR DIAGNOSTICS MODAL -->
  <div class="modal-backdrop" id="doctorModal">
    <div class="modal-card" style="max-width:455px;">
      <div style="display:flex; align-items:center; justify-content:space-between; gap:8px;">
        <div style="font-size:16px; font-weight:700;" data-i18n="doctor_title">Diagnóstico del Sistema</div>
        <span class="badge badge-neutral" id="doctorModalSummary">...</span>
      </div>
      <div class="doctor-list" id="doctorProbesList"></div>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" onclick="closeDoctorModal()" data-i18n="doctor_close">Cerrar</button>
        <button type="button" class="btn btn-primary" onclick="runQuickDoctor()" data-i18n="doctor_rerun">Volver a comprobar</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toastBox"></div>

<script>
const PRADO_TOKEN = "__PRADO_SESSION_TOKEN__";
let currentLang = "es";
let appState = null;
let formInitialized = false;
let credsExpanded = true;
let activeCardTab = "account";
let lastDoctorSeq = null;

const I18N = {
  es: {
    dash_title: "PradoOS — Configuración UGR",
    subtitle_tray: "Barra de Menús / System Tray",
    tab_account: "Cuenta y Carpeta",
    tab_prefs: "Correo y Opciones",
    status_unconfigured: "Cuenta UGR pendiente de configurar",
    badge_setup_pending: "Pendiente",
    badge_idle: "Al día",
    badge_syncing: "Sincronizando...",
    badge_error: "Error",
    courses_unit: "asignaturas",
    files_unit: "archivos",
    last_sync_prefix: "Última sinc.:",
    btn_edit_creds: "Cambiar contraseña",
    btn_hide_creds: "Ocultar",
    connected_keychain: "Contraseña en Llavero seguro",
    onb_email: "Correo Institucional UGR",
    ph_email: "usuario@correo.ugr.es",
    onb_portal: "Portal PRADO",
    opt_portal_grado: "Grado (pradogrado)",
    opt_portal_posgrado: "Posgrado / Máster",
    opt_portal_ceprud: "CEPRUD / Otros",
    onb_password: "Contraseña PRADO (Acceso Identificado)",
    keychain_hint: "Solo local · Llavero nativo",
    onb_folder: "Carpeta Local de Apuntes",
    btn_browse: "Elegir...",
    lbl_preset_mode: "Organización de Carpetas",
    seg_mirror: "Mirror (PRADO oficial)",
    seg_smart: "Smart (Teoría / Prácticas)",
    tree_mirror_desc: "Mantiene las carpetas exactas creadas en PRADO.",
    tree_smart_desc: "Organiza automáticamente en Teoría, Prácticas y General.",
    lbl_fwd_enable: "Reenviar correos de profesores (@correo.ugr.es) a mi correo personal:",
    ph_fwd_email: "tu.correo@gmail.com",
    fwd_helper: "Se filtra el correo académico de PRADO y profesores sin reenviar spam.",
    lbl_notif_title: "Notificaciones de escritorio (nuevos apuntes y entregas)",
    lbl_autostart: "Abrir PradoOS al iniciar sesión",
    lbl_autosync_freq: "Sincronización automática en segundo plano",
    opt_autosync_off: "Desactivada (manual desde la barra)",
    opt_autosync_30: "Cada 30 minutos",
    opt_autosync_60: "Cada 1 hora (Recomendado)",
    opt_autosync_120: "Cada 2 horas",
    btn_run_doctor: "Diagnóstico",
    btn_logout: "Cerrar sesión",
    doctor_title: "Diagnóstico del Sistema",
    doctor_running: "Ejecutando comprobaciones del sistema...",
    doctor_close: "Cerrar",
    doctor_rerun: "Volver a comprobar",
    doctor_ok: "Diagnóstico correcto: {ok}/{total} comprobaciones OK.",
    doctor_warn: "Diagnóstico: {ok}/{total} OK — revisa permisos o sesión.",
    toast_logged_out: "Sesión cerrada. Introduce una cuenta UGR para volver a conectar.",
    sync_in_progress: "Sincronizando con PRADO UGR...",
    btn_open_folder: "Abrir Carpeta",
    onb_submit: "Guardar y Sincronizar",
    prefs_submit: "Guardar Opciones",
    toast_saved_syncing: "Configuración guardada. Sincronización iniciada...",
    toast_prefs_saved: "Opciones guardadas correctamente.",
    toast_save_error: "Error al guardar la configuración",
    mfa_title: "Verificación en 2 Pasos (MFA UGR)",
    mfa_prompt_default: "Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es. Tu dispositivo quedará verificado por 30 días.",
    mfa_help_hint: "Si no llega en 30 segundos, revisa Correo no deseado en @correo.ugr.es.",
    mfa_cancel_btn: "Cancelar",
    mfa_verify_btn: "Verificar (30 días)",
    toast_mfa_ok: "Código MFA enviado. Dispositivo verificado por 30 días."
  },
  en: {
    dash_title: "PradoOS — UGR Setup",
    subtitle_tray: "Menu Bar / System Tray",
    tab_account: "Account & Folder",
    tab_prefs: "Mail & Preferences",
    status_unconfigured: "UGR Account not configured yet",
    badge_setup_pending: "Setup pending",
    badge_idle: "Up to date",
    badge_syncing: "Syncing...",
    badge_error: "Error",
    courses_unit: "courses",
    files_unit: "files",
    last_sync_prefix: "Last sync:",
    btn_edit_creds: "Change password",
    btn_hide_creds: "Hide",
    connected_keychain: "Password stored in OS Keychain",
    onb_email: "Institutional UGR Email",
    ph_email: "user@correo.ugr.es",
    onb_portal: "PRADO Portal",
    opt_portal_grado: "Undergraduate (pradogrado)",
    opt_portal_posgrado: "Postgraduate / Master",
    opt_portal_ceprud: "CEPRUD / Other",
    onb_password: "PRADO Password (SSO)",
    keychain_hint: "Local only · OS Keychain",
    onb_folder: "Local Courses Folder",
    btn_browse: "Browse...",
    lbl_preset_mode: "Folder Organization",
    seg_mirror: "Mirror (Official PRADO)",
    seg_smart: "Smart (Theory / Labs)",
    tree_mirror_desc: "Keeps the exact section layout from PRADO.",
    tree_smart_desc: "Auto-sorts files into clean Theory and Labs folders.",
    lbl_fwd_enable: "Auto-forward professor emails (@correo.ugr.es) to my personal inbox:",
    ph_fwd_email: "your.email@gmail.com",
    fwd_helper: "Forwards academic and PRADO notices without passing spam.",
    lbl_notif_title: "Desktop notifications (new notes and deadlines)",
    lbl_autostart: "Launch PradoOS at login",
    lbl_autosync_freq: "Background auto-sync",
    opt_autosync_off: "Off (manual sync from menu bar)",
    opt_autosync_30: "Every 30 minutes",
    opt_autosync_60: "Every 1 hour (Recommended)",
    opt_autosync_120: "Every 2 hours",
    btn_run_doctor: "Diagnostics",
    btn_logout: "Log out",
    doctor_title: "System Diagnostics",
    doctor_running: "Running health checks...",
    doctor_close: "Close",
    doctor_rerun: "Run Again",
    doctor_ok: "Health check passed: {ok}/{total} probes OK.",
    doctor_warn: "Health check: {ok}/{total} OK — check permissions or session.",
    toast_logged_out: "Signed out. Enter your UGR account to reconnect.",
    sync_in_progress: "Syncing with PRADO UGR...",
    btn_open_folder: "Open Folder",
    onb_submit: "Save & Sync Now",
    prefs_submit: "Save Preferences",
    toast_saved_syncing: "Configuration saved. Synchronization started...",
    toast_prefs_saved: "Preferences saved.",
    toast_save_error: "Could not save configuration",
    mfa_title: "2-Step Verification (UGR MFA)",
    mfa_prompt_default: "Enter the 6-digit code sent to your @correo.ugr.es inbox. Your device will stay trusted for 30 days.",
    mfa_help_hint: "If not received within 30 seconds, check Spam in @correo.ugr.es.",
    mfa_cancel_btn: "Cancel",
    mfa_verify_btn: "Verify Device (30 days)",
    toast_mfa_ok: "MFA code submitted. Device verified for 30 days."
  },
  it: {
    dash_title: "PradoOS — Configurazione UGR",
    subtitle_tray: "Barra dei Menu / System Tray",
    tab_account: "Account e Cartella",
    tab_prefs: "Posta e Opzioni",
    status_unconfigured: "Account UGR da configurare",
    badge_setup_pending: "Da configurare",
    badge_idle: "Aggiornato",
    badge_syncing: "Sincronizzazione...",
    badge_error: "Errore",
    courses_unit: "corsi",
    files_unit: "file",
    last_sync_prefix: "Ultima sinc.:",
    btn_edit_creds: "Cambia password",
    btn_hide_creds: "Nascondi",
    connected_keychain: "Password nel Portachiavi locale",
    onb_email: "Email Istituzionale UGR",
    ph_email: "utente@correo.ugr.es",
    onb_portal: "Portale PRADO",
    opt_portal_grado: "Triennale / Grado (pradogrado)",
    opt_portal_posgrado: "Magistrale / Posgrado",
    opt_portal_ceprud: "CEPRUD / Altri",
    onb_password: "Password PRADO (SSO)",
    keychain_hint: "Solo locale · Portachiavi OS",
    onb_folder: "Cartella Locale dei Corsi",
    btn_browse: "Scegli...",
    lbl_preset_mode: "Organizzazione Cartelle",
    seg_mirror: "Mirror (PRADO ufficiale)",
    seg_smart: "Smart (Teoria / Pratiche)",
    tree_mirror_desc: "Mantiene la struttura esatta creata su PRADO.",
    tree_smart_desc: "Separa automaticamente in Teoria, Pratiche e Generale.",
    lbl_fwd_enable: "Inoltra le email dei docenti (@correo.ugr.es) alla mia email:",
    ph_fwd_email: "tua.email@gmail.com",
    fwd_helper: "Inoltra solo avvisi accademici e PRADO filtrando lo spam.",
    lbl_notif_title: "Notifiche desktop (nuovi appunti e scadenze)",
    lbl_autostart: "Avvia PradoOS all'accesso",
    lbl_autosync_freq: "Sincronizzazione automatica in background",
    opt_autosync_off: "Disattivata (manuale dal menu)",
    opt_autosync_30: "Ogni 30 minuti",
    opt_autosync_60: "Ogni 1 ora (Consigliato)",
    opt_autosync_120: "Ogni 2 ore",
    btn_run_doctor: "Diagnostica",
    btn_logout: "Disconnetti",
    doctor_title: "Diagnostica Sistema",
    doctor_running: "Verifica controlli in corso...",
    doctor_close: "Chiudi",
    doctor_rerun: "Esegui di nuovo",
    doctor_ok: "Diagnostica superata: {ok}/{total} controlli OK.",
    doctor_warn: "Diagnostica: {ok}/{total} OK — controlla permessi o sessione.",
    toast_logged_out: "Disconnesso. Inserisci un account UGR per ricollegarti.",
    sync_in_progress: "Sincronizzazione con PRADO UGR...",
    btn_open_folder: "Apri Cartella",
    onb_submit: "Salva e Sincronizza",
    prefs_submit: "Salva Opzioni",
    toast_saved_syncing: "Configurazione salvata. Sincronizzazione avviata...",
    toast_prefs_saved: "Opzioni salvate correttamente.",
    toast_save_error: "Impossibile salvare la configurazione",
    mfa_title: "Verifica in 2 Passaggi (MFA UGR)",
    mfa_prompt_default: "Inserisci il codice a 6 cifre inviato alla tua email @correo.ugr.es. Il dispositivo resterà verificato per 30 giorni.",
    mfa_help_hint: "Se non arriva entro 30 secondi, controlla lo Spam su @correo.ugr.es.",
    mfa_cancel_btn: "Annulla",
    mfa_verify_btn: "Verifica (30 giorni)",
    toast_mfa_ok: "Codice MFA inviato. Dispositivo verificato per 30 giorni."
  },
  fr: {
    dash_title: "PradoOS — Configuration UGR",
    subtitle_tray: "Barre des Menus / Zone de Notification",
    tab_account: "Compte et Dossier",
    tab_prefs: "Courriel et Options",
    status_unconfigured: "Compte UGR à configurer",
    badge_setup_pending: "À configurer",
    badge_idle: "À jour",
    badge_syncing: "Synchronisation...",
    badge_error: "Erreur",
    courses_unit: "cours",
    files_unit: "fichiers",
    last_sync_prefix: "Dernière sync :",
    btn_edit_creds: "Changer mot de passe",
    btn_hide_creds: "Masquer",
    connected_keychain: "Mot de passe dans le Trousseau",
    onb_email: "Courriel Institutionnel UGR",
    ph_email: "utilisateur@correo.ugr.es",
    onb_portal: "Portail PRADO",
    opt_portal_grado: "Licence / Grado (pradogrado)",
    opt_portal_posgrado: "Master / Posgrado",
    opt_portal_ceprud: "CEPRUD / Autres",
    onb_password: "Mot de passe PRADO (SSO)",
    keychain_hint: "Local uniquement · Trousseau",
    onb_folder: "Dossier Local des Cours",
    btn_browse: "Parcourir...",
    lbl_preset_mode: "Organisation des Dossiers",
    seg_mirror: "Mirror (PRADO officiel)",
    seg_smart: "Smart (Théorie / TP)",
    tree_mirror_desc: "Conserve la structure exacte de PRADO.",
    tree_smart_desc: "Classe automatiquement en Théorie, TP et Général.",
    lbl_fwd_enable: "Rediriger les courriels des professeurs (@correo.ugr.es) vers mon courriel :",
    ph_fwd_email: "votre.email@gmail.com",
    fwd_helper: "Transfère uniquement les messages académiques en filtrant le spam.",
    lbl_notif_title: "Notifications du bureau (nouveaux cours et échéances)",
    lbl_autostart: "Lancer PradoOS à l'ouverture de session",
    lbl_autosync_freq: "Synchronisation automatique en arrière-plan",
    opt_autosync_off: "Désactivée (manuelle depuis la barre)",
    opt_autosync_30: "Toutes les 30 minutes",
    opt_autosync_60: "Toutes les heures (Recommandé)",
    opt_autosync_120: "Toutes les 2 heures",
    btn_run_doctor: "Diagnostic",
    btn_logout: "Déconnexion",
    doctor_title: "Diagnostic Système",
    doctor_running: "Vérifications en cours...",
    doctor_close: "Fermer",
    doctor_rerun: "Relancer",
    doctor_ok: "Diagnostic réussi : {ok}/{total} vérifications OK.",
    doctor_warn: "Diagnostic : {ok}/{total} OK — vérifiez les permissions ou la session.",
    toast_logged_out: "Déconnecté. Saisissez un compte UGR pour vous reconnecter.",
    sync_in_progress: "Synchronisation avec PRADO UGR...",
    btn_open_folder: "Ouvrir Dossier",
    onb_submit: "Enregistrer et Synchroniser",
    prefs_submit: "Enregistrer Options",
    toast_saved_syncing: "Configuration enregistrée. Synchronisation en cours...",
    toast_prefs_saved: "Options enregistrées.",
    toast_save_error: "Erreur lors de l'enregistrement",
    mfa_title: "Validation en 2 Étapes (MFA UGR)",
    mfa_prompt_default: "Saisissez le code à 6 chiffres envoyé à @correo.ugr.es. Votre appareil restera approuvé pendant 30 jours.",
    mfa_help_hint: "Sans réception après 30 s, vérifiez les courriers indésirables.",
    mfa_cancel_btn: "Annuler",
    mfa_verify_btn: "Approuver (30 jours)",
    toast_mfa_ok: "Code MFA envoyé. Appareil approuvé pour 30 jours."
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

function switchCardTab(tabName) {
  const isAccount = tabName !== "prefs";
  activeCardTab = isAccount ? "account" : "prefs";
  document.getElementById("tabBtnAccount").classList.toggle("active", isAccount);
  document.getElementById("tabBtnPrefs").classList.toggle("active", !isAccount);
  document.getElementById("cardTabAccount").classList.toggle("active", isAccount);
  document.getElementById("cardTabPrefs").classList.toggle("active", !isAccount);
  const dict = I18N[currentLang] || I18N.es;
  const btnSync = document.getElementById("btnSyncNow");
  if (btnSync) {
    btnSync.textContent = isAccount ? dict.onb_submit : dict.prefs_submit;
  }
  if (appState) renderStateText(appState);
}

function togglePasswordVisibility() {
  const pw = document.getElementById("onbPassword");
  pw.type = pw.type === "password" ? "text" : "password";
}

function toggleCredentialsEditor(forceState) {
  const wrap = document.getElementById("credentialsFieldsWrap");
  const connCard = document.getElementById("connectedSummaryCard");
  const cancelBtn = document.getElementById("btnCancelCredsEdit");
  const isConnected = Boolean(appState && (appState.is_onboarded || appState.auth.username));
  credsExpanded = typeof forceState === "boolean" ? forceState : !credsExpanded;
  wrap.classList.toggle("collapsed", !credsExpanded);
  if (connCard) {
    connCard.classList.toggle("visible", isConnected && !credsExpanded);
  }
  if (cancelBtn) {
    cancelBtn.style.display = isConnected && credsExpanded ? "inline-flex" : "none";
  }
  if (appState) renderStateText(appState);
}

function setPresetMode(mode) {
  const clean = mode === "smart" ? "smart" : "mirror";
  document.getElementById("onbPreset").value = clean;
  document.getElementById("segMirror").classList.toggle("active", clean === "mirror");
  document.getElementById("segSmart").classList.toggle("active", clean === "smart");
  updateTreePreview();
}

function updateTreePreview() {
  const dict = I18N[currentLang] || I18N.es;
  const preset = document.getElementById("onbPreset").value === "smart" ? "smart" : "mirror";
  const rawRoot = (document.getElementById("onbCoursesRoot").value || "UGR_Courses").trim();
  const baseName = rawRoot.split(/[\\/]/).filter(Boolean).pop() || "UGR_Courses";
  document.getElementById("treePreviewDesc").textContent =
    preset === "smart" ? dict.tree_smart_desc : dict.tree_mirror_desc;
  const lines = preset === "smart"
    ? `${esc(baseName)}/<br>└─ Estructura_de_Datos/<br>&nbsp;&nbsp;&nbsp;├─ Teoría/ · Tema1.pdf<br>&nbsp;&nbsp;&nbsp;└─ Prácticas/ · P1_STL.zip`
    : `${esc(baseName)}/<br>└─ Estructura_de_Datos/<br>&nbsp;&nbsp;&nbsp;├─ Tema_1_Introduccion/<br>&nbsp;&nbsp;&nbsp;└─ Practicas_Grupo_C/`;
  document.getElementById("treePreviewLines").innerHTML = lines;
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
  const btnSync = document.getElementById("btnSyncNow");
  if (btnSync) {
    btnSync.textContent = activeCardTab === "account" ? dict.onb_submit : dict.prefs_submit;
  }
  updateTreePreview();
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
  switchCardTab("account");
  if (field === "username" || field === "password") {
    toggleCredentialsEditor(true);
  }
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

function openOnboardingModal() {
  document.getElementById("onboardingModal").classList.add("visible");
}

function closeOnboardingModal() {
  document.getElementById("onboardingModal").classList.remove("visible");
}

async function pickFolderFor(inputId) {
  const res = await apiPost("/api/folder/pick", {});
  if (res.status === "success" && res.path) {
    document.getElementById(inputId).value = res.path;
    updateTreePreview();
  }
}

async function openCoursesFolder() {
  await apiPost("/api/folder/open", {});
}

function closeDoctorModal() {
  document.getElementById("doctorModal").classList.remove("visible");
}

function openDoctorFromTray() {
  switchCardTab("prefs");
  runQuickDoctor();
}

async function runQuickDoctor() {
  const dict = I18N[currentLang] || I18N.es;
  const out = document.getElementById("doctorQuickResult");
  const modal = document.getElementById("doctorModal");
  const listEl = document.getElementById("doctorProbesList");
  const sumEl = document.getElementById("doctorModalSummary");

  out.textContent = dict.doctor_running;
  out.style.color = "var(--text-muted)";
  out.style.display = "block";

  if (modal && listEl && sumEl) {
    sumEl.className = "badge badge-neutral";
    sumEl.textContent = "...";
    listEl.innerHTML = `<div class="helper-text" style="padding:10px 4px;">${dict.doctor_running}</div>`;
    modal.classList.add("visible");
  }

  const res = await apiGet("/api/doctor");
  if (res.status === "success") {
    const probes = res.probes || [];
    const okCount = probes.filter(p => (p.status || "").toUpperCase() === "OK" || p.ok === true).length;
    const allOk = okCount === probes.length;
    const tpl = allOk ? dict.doctor_ok : dict.doctor_warn;
    out.textContent = tpl.replace("{ok}", String(okCount)).replace("{total}", String(probes.length));
    out.style.color = allOk ? "var(--green)" : "var(--amber)";
    out.style.display = "block";

    if (sumEl && listEl) {
      sumEl.className = allOk ? "badge badge-ok" : "badge badge-error";
      sumEl.textContent = `${okCount}/${probes.length} OK`;
      listEl.innerHTML = "";
      probes.forEach(p => {
        const st = String(p.status || (p.ok ? "OK" : "FAIL")).toUpperCase();
        const cls = st === "OK" ? "ok" : (st === "WARN" || st === "SKIP" ? "warn" : "fail");
        const row = document.createElement("div");
        row.className = "doctor-row";
        const pill = document.createElement("span");
        pill.className = `doctor-pill ${cls}`;
        pill.textContent = st;
        const body = document.createElement("div");
        body.style.minWidth = "0";
        const title = document.createElement("div");
        title.style.fontWeight = "600";
        title.textContent = p.name || p.probe_id || "";
        const msg = document.createElement("div");
        msg.className = "helper-text";
        msg.textContent = p.message || "";
        body.appendChild(title);
        body.appendChild(msg);
        if (st !== "OK" && p.remediation) {
          const rem = document.createElement("div");
          rem.className = "helper-text";
          rem.style.color = "var(--accent)";
          rem.textContent = p.remediation;
          body.appendChild(rem);
        }
        row.appendChild(pill);
        row.appendChild(body);
        listEl.appendChild(row);
      });
    }
  }
}

async function logoutAccount() {
  const dict = I18N[currentLang] || I18N.es;
  const res = await apiPost("/api/auth/logout", {});
  if (res.status === "success") {
    document.getElementById("onbPassword").value = "";
    toggleCredentialsEditor(true);
    showToast(dict.toast_logged_out);
    refreshState();
  }
}

async function toggleNotificationsImmediate(enabled) {
  const dict = I18N[currentLang] || I18N.es;
  const res = await apiPost("/api/notifications/toggle", { enabled: Boolean(enabled) });
  if (res.status === "success") {
    showToast(dict.toast_prefs_saved);
  } else {
    showToast(res.error || dict.toast_save_error);
  }
}

async function toggleAutostartImmediate(enabled) {
  const dict = I18N[currentLang] || I18N.es;
  const res = await apiPost("/api/autostart/toggle", { enabled: Boolean(enabled) });
  if (res.status === "success") {
    showToast(dict.toast_prefs_saved);
  } else {
    document.getElementById("onbAutostart").checked = !Boolean(enabled);
    showToast(res.error || dict.toast_save_error);
  }
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
  const autostart = document.getElementById("onbAutostart").checked;
  const autoVal = document.getElementById("onbAutoSyncSelect").value;
  const autoSync = autoVal !== "off";
  const autoMins = autoSync ? parseInt(autoVal, 10) : 60;
  const fwdEnabled = document.getElementById("cfgFwdEnabled").checked;
  const fwdTo = document.getElementById("cfgFwdTo").value.trim();

  await apiPost("/api/mail/forwarding", {
    forward_enabled: fwdEnabled,
    forward_to: fwdTo,
    forward_mode: "academic"
  });

  const shouldSync = activeCardTab === "account";
  const res = await apiPost("/api/onboard", {
    language: currentLang,
    portal: portal,
    username: username,
    password: password,
    courses_root: coursesRoot,
    preset: preset,
    notifications_enabled: notif,
    autostart: autostart,
    auto_sync: autoSync,
    auto_sync_interval_minutes: autoMins,
    start_sync: shouldSync
  });

  if (res.status === "success") {
    showToast(shouldSync ? dict.toast_saved_syncing : dict.toast_prefs_saved);
    if (res.username) {
      toggleCredentialsEditor(false);
    }
    refreshState();
  } else {
    const msg = res.error || dict.toast_save_error;
    showFieldError(res.field || "", msg);
    showToast(msg);
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
    document.getElementById("mfaCodeInput").focus();
    showToast(res.error);
  }
}

async function cancelMfaModal() {
  await apiPost("/api/auth/mfa/cancel", {});
  document.getElementById("mfaCodeInput").value = "";
  const errMfa = document.getElementById("err-mfa");
  if (errMfa) { errMfa.textContent = ""; errMfa.classList.remove("visible"); }
  document.getElementById("mfaModal").classList.remove("visible");
  refreshState();
}

document.getElementById("mfaCodeInput").addEventListener("keydown", function (ev) {
  if (ev.key === "Enter") {
    ev.preventDefault();
    submitMfaCode();
  }
});

function renderStateText(st) {
  const dict = I18N[currentLang] || I18N.es;
  const isConfigured = Boolean(st.is_onboarded || st.auth.username);
  const isConnected = isConfigured;
  document.getElementById("versionLabel").textContent = `v${st.version} · ${dict.subtitle_tray}`;
  document.getElementById("sidebarUser").textContent = st.auth.username
    ? `${st.auth.username} (${st.stats.active_courses} ${dict.courses_unit})`
    : dict.status_unconfigured;
  document.getElementById("lastSyncLabel").textContent = `${dict.last_sync_prefix} ${st.sync.last_sync_time || "--:--"}`;

  const unconfigStrip = document.getElementById("unconfiguredStrip");
  const connCard = document.getElementById("connectedSummaryCard");
  const cancelBtn = document.getElementById("btnCancelCredsEdit");
  const logoutBtn = document.getElementById("btnLogoutQuick");
  if (isConnected) {
    connCard.classList.toggle("visible", !credsExpanded);
    if (unconfigStrip) {
      unconfigStrip.style.display = (activeCardTab === "prefs" || credsExpanded) ? "flex" : "none";
    }
    if (cancelBtn) cancelBtn.style.display = credsExpanded ? "inline-flex" : "none";
    document.getElementById("connectedUserText").textContent = st.auth.username;
    const portalKey = st.auth.portal === "posgrado" ? "opt_portal_posgrado" : (st.auth.portal === "ceprud" ? "opt_portal_ceprud" : "opt_portal_grado");
    document.getElementById("connectedSubText").textContent =
      `${st.stats.active_courses} ${dict.courses_unit} · ${dict[portalKey] || st.auth.portal} · ${dict.connected_keychain}`;
    if (logoutBtn) logoutBtn.style.display = "inline-flex";
  } else {
    connCard.classList.remove("visible");
    if (unconfigStrip) unconfigStrip.style.display = "flex";
    if (cancelBtn) cancelBtn.style.display = "none";
    if (logoutBtn) logoutBtn.style.display = "none";
  }

  const badge = document.getElementById("syncStatusBadge");
  const badgeConn = document.getElementById("syncStatusBadgeConn");
  const progWrap = document.getElementById("syncProgressWrap");
  const progBar = document.getElementById("syncProgressBar");
  const btnSync = document.getElementById("btnSyncNow");

  let bClass = "badge badge-idle";
  let bText = `${dict.badge_idle} (${st.stats.total_files} ${dict.files_unit})`;
  if (st.sync.status === "syncing" || st.sync.status === "mfa_required") {
    bClass = "badge badge-syncing";
    bText = dict.badge_syncing;
    progWrap.classList.add("visible");
    progBar.style.width = `${st.sync.progress_pct || 15}%`;
    document.getElementById("syncStepText").textContent = st.sync.current_step || dict.sync_in_progress;
    btnSync.disabled = true;
  } else if (st.sync.status === "error") {
    bClass = "badge badge-error";
    bText = dict.badge_error;
    progWrap.classList.remove("visible");
    btnSync.disabled = false;
  } else if (!isConfigured) {
    bClass = "badge badge-neutral";
    bText = dict.badge_setup_pending;
    progWrap.classList.remove("visible");
    btnSync.disabled = false;
  } else {
    progWrap.classList.remove("visible");
    btnSync.disabled = false;
  }
  badge.className = bClass;
  badge.textContent = bText;
  if (badgeConn) {
    badgeConn.className = bClass;
    badgeConn.textContent = bText;
  }
}

async function refreshState() {
  try {
    const st = await apiGet("/api/state");
    appState = st;

    if (!formInitialized) {
      formInitialized = true;
      const isConnected = Boolean(st.is_onboarded || st.auth.username);
      credsExpanded = !isConnected;
      document.getElementById("credentialsFieldsWrap").classList.toggle("collapsed", !credsExpanded);
      applyTranslations(st.language || "es");
      document.getElementById("onbPortal").value = st.auth.portal || "grado";
      document.getElementById("onbUsername").value = st.auth.username || "";
      document.getElementById("onbCoursesRoot").value = st.config.courses_root || "";
      setPresetMode(st.config.preset || "mirror");
      document.getElementById("onbNotifications").checked = Boolean(st.config.notifications_enabled);
      document.getElementById("onbAutostart").checked = Boolean(st.config.autostart);
      const autoSel = document.getElementById("onbAutoSyncSelect");
      if (autoSel) {
        if (!st.config.auto_sync) autoSel.value = "off";
        else autoSel.value = String(st.config.auto_sync_interval_minutes || 60);
      }
      document.getElementById("cfgFwdEnabled").checked = Boolean(st.config.mail.forward_enabled);
      document.getElementById("cfgFwdTo").value = st.config.mail.forward_to || "";
    }

    renderStateText(st);

    const docSeq = Number((st.ui && st.ui.doctor_trigger_seq) || 0);
    if (lastDoctorSeq === null) {
      lastDoctorSeq = docSeq;
    } else if (docSeq > lastDoctorSeq) {
      lastDoctorSeq = docSeq;
      openDoctorFromTray();
    }

    const mfaModal = document.getElementById("mfaModal");
    if (st.sync.mfa_pending) {
      const dict = I18N[currentLang] || I18N.es;
      const wasHidden = !mfaModal.classList.contains("visible");
      document.getElementById("mfaPromptText").textContent = st.sync.mfa_prompt || dict.mfa_prompt_default;
      mfaModal.classList.add("visible");
      if (wasHidden) {
        setTimeout(() => document.getElementById("mfaCodeInput").focus(), 40);
      }
    } else {
      mfaModal.classList.remove("visible");
    }
  } catch (e) {}
}

refreshState();
setInterval(refreshState, 1500);
window.addEventListener("focus", refreshState);
if (window.location.hash === "#doctor") {
  setTimeout(() => openDoctorFromTray(), 250);
}
</script>
</body>
</html>
"""
