"""
PradoOS Control Center Single-Page Application (HTML5 / CSS3 / Vanilla ES2022).

Zero external network dependencies (100% self-contained for instant local rendering
in `pywebview` WebKit/WebView2 or any desktop browser).
Supports 4 languages (`es`, `en`, `it`, `fr`) and automatic Dark/Light themes.
"""

from __future__ import annotations


def render_control_center_html(token: str) -> str:
    """Renders the complete PradoOS Control Center HTML document with injected session token."""
    return _HTML_TEMPLATE.replace("__PRADO_SESSION_TOKEN__", token)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PradoOS — Centro de Control Académico UGR</title>
<style>
  :root {
    --bg-app: #0f1117;
    --bg-sidebar: #151821;
    --bg-card: #1a1d28;
    --bg-card-hover: #212534;
    --bg-input: #11131a;
    --border: #2a2f42;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --accent: #d91b42;
    --accent-hover: #f02850;
    --accent-soft: rgba(217, 27, 66, 0.14);
    --green: #10b981;
    --green-soft: rgba(16, 185, 129, 0.15);
    --amber: #f59e0b;
    --amber-soft: rgba(245, 158, 11, 0.15);
    --red: #ef4444;
    --red-soft: rgba(239, 68, 68, 0.15);
    --blue: #3b82f6;
    --blue-soft: rgba(59, 130, 246, 0.15);
    --radius: 12px;
    --shadow: 0 8px 24px rgba(0, 0, 0, 0.32);
  }
  @media (prefers-color-scheme: light) {
    :root {
      --bg-app: #f5f6fa;
      --bg-sidebar: #ffffff;
      --bg-card: #ffffff;
      --bg-card-hover: #f9fafb;
      --bg-input: #f3f4f6;
      --border: #e5e7eb;
      --text-main: #111827;
      --text-muted: #6b7280;
      --accent: #b20029;
      --accent-hover: #900020;
      --accent-soft: rgba(178, 0, 41, 0.09);
      --shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
    }
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg-app);
    color: var(--text-main);
    display: flex;
    height: 100vh;
    overflow: hidden;
    user-select: none;
    -webkit-font-smoothing: antialiased;
  }
  /* Sidebar */
  .sidebar {
    width: 250px;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 20px 14px;
    flex-shrink: 0;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 10px 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
  }
  .brand-logo {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: var(--accent);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(217, 27, 66, 0.35);
  }
  .brand-title { font-size: 16px; font-weight: 700; letter-spacing: -0.02em; }
  .brand-sub { font-size: 11px; color: var(--text-muted); }
  .nav-list { list-style: none; display: flex; flex-direction: column; gap: 6px; flex: 1; }
  .nav-btn {
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 11px 12px;
    border-radius: 9px;
    font-size: 13.5px;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: all 0.15s ease;
  }
  .nav-btn:hover { background: var(--bg-card-hover); color: var(--text-main); }
  .nav-btn.active {
    background: var(--accent-soft);
    color: var(--accent);
    font-weight: 600;
  }
  .sidebar-footer {
    border-top: 1px solid var(--border);
    padding-top: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .user-pill {
    font-size: 12px;
    color: var(--text-muted);
    background: var(--bg-input);
    padding: 8px 10px;
    border-radius: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .lang-row {
    display: flex;
    gap: 4px;
  }
  .lang-btn {
    flex: 1;
    padding: 6px 0;
    font-size: 11px;
    font-weight: 600;
    background: var(--bg-input);
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
  }
  .lang-btn.active {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }
  /* Main Content Area */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 26px 32px;
    gap: 22px;
  }
  .view-section { display: none; flex-direction: column; gap: 20px; }
  .view-section.active { display: flex; }
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .page-title { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
  .page-subtitle { font-size: 13px; color: var(--text-muted); margin-top: 3px; }
  /* Cards & Grids */
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
  }
  .card-title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
  }
  .kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
  }
  .kpi-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
  .kpi-val { font-size: 26px; font-weight: 700; margin-top: 6px; }
  .two-col {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 18px;
  }
  /* Buttons & Inputs */
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 9px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s ease;
  }
  .btn:disabled { opacity: 0.55; cursor: not-allowed; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
  .btn-secondary {
    background: var(--bg-input);
    color: var(--text-main);
    border-color: var(--border);
  }
  .btn-secondary:hover:not(:disabled) { background: var(--bg-card-hover); }
  .btn-sm { padding: 6px 11px; font-size: 12px; border-radius: 6px; }
  .input, .select {
    width: 100%;
    padding: 9px 12px;
    background: var(--bg-input);
    color: var(--text-main);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 13px;
    outline: none;
  }
  .input:focus, .select:focus { border-color: var(--accent); }
  .form-group { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
  .form-label { font-size: 12.5px; font-weight: 600; color: var(--text-muted); }
  .row { display: flex; align-items: center; gap: 10px; }
  /* Status Badges */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
  }
  .badge-idle { background: var(--green-soft); color: var(--green); }
  .badge-syncing { background: var(--amber-soft); color: var(--amber); }
  .badge-error { background: var(--red-soft); color: var(--red); }
  .badge-info { background: var(--blue-soft); color: var(--blue); }
  /* Progress Bar & Logs */
  .progress-wrap {
    margin-top: 14px;
    display: none;
    flex-direction: column;
    gap: 8px;
  }
  .progress-wrap.visible { display: flex; }
  .progress-bar-bg {
    width: 100%;
    height: 8px;
    background: var(--bg-input);
    border-radius: 999px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--amber));
    width: 0%;
    transition: width 0.3s ease;
  }
  .log-box {
    margin-top: 10px;
    background: #0b0d12;
    color: #d1d5db;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 11.5px;
    padding: 12px;
    border-radius: 8px;
    max-height: 170px;
    overflow-y: auto;
    border: 1px solid var(--border);
    user-select: text;
    white-space: pre-wrap;
  }
  /* Lists & Tables */
  .item-list { display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; }
  .list-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 11px 13px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 9px;
  }
  .list-row-title { font-size: 13px; font-weight: 600; }
  .list-row-sub { font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }
  /* Mail Split Pane */
  .mail-split {
    display: grid;
    grid-template-columns: 340px 1fr;
    gap: 16px;
    height: 430px;
  }
  .mail-list {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }
  .mail-item {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.12s;
  }
  .mail-item:hover { background: var(--bg-card-hover); }
  .mail-item.active { background: var(--accent-soft); }
  .mail-item-subj { font-size: 13px; font-weight: 600; margin-bottom: 3px; }
  .mail-item-meta { font-size: 11.5px; color: var(--text-muted); display: flex; justify-content: space-between; }
  .mail-viewer {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    user-select: text;
  }
  .mail-body {
    margin-top: 14px;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
    flex: 1;
    overflow-y: auto;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  /* Modals (Onboarding & MFA) */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(5px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .modal-backdrop.visible { display: flex; }
  .modal-card {
    width: 540px;
    max-width: 94vw;
    max-height: 92vh;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 26px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  }
  .toast {
    position: fixed;
    bottom: 22px;
    right: 24px;
    background: var(--bg-card);
    color: var(--text-main);
    border: 1px solid var(--accent);
    padding: 12px 18px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    box-shadow: var(--shadow);
    display: none;
    z-index: 2000;
  }
  .toast.visible { display: block; }
</style>
</head>
<body>

  <!-- Sidebar Navigation -->
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">🎓</div>
      <div>
        <div class="brand-title">PradoOS</div>
        <div class="brand-sub" id="versionLabel">v0.2.0 • UGR Engine</div>
      </div>
    </div>

    <ul class="nav-list">
      <li><button class="nav-btn active" onclick="switchTab('dashboard')" id="nav-dashboard">🏠 <span data-i18n="nav_dashboard">Panel Principal</span></button></li>
      <li><button class="nav-btn" onclick="switchTab('courses')" id="nav-courses">📚 <span data-i18n="nav_courses">Mis Asignaturas</span></button></li>
      <li><button class="nav-btn" onclick="switchTab('mail')" id="nav-mail">📬 <span data-i18n="nav_mail">Correo UGR y Reenvío</span></button></li>
      <li><button class="nav-btn" onclick="switchTab('calendar')" id="nav-calendar">📅 <span data-i18n="nav_calendar">Calendario y Sistema</span></button></li>
    </ul>

    <div class="sidebar-footer">
      <div class="user-pill" id="sidebarUser">No conectado</div>
      <button class="btn btn-secondary btn-sm" onclick="openOnboardingModal(true)" style="width:100%;">⚙️ <span data-i18n="btn_setup_account">Configurar Cuenta UGR</span></button>
      <div class="lang-row">
        <button class="lang-btn" id="lang-es" onclick="setLanguage('es')">ES</button>
        <button class="lang-btn" id="lang-en" onclick="setLanguage('en')">EN</button>
        <button class="lang-btn" id="lang-it" onclick="setLanguage('it')">IT</button>
        <button class="lang-btn" id="lang-fr" onclick="setLanguage('fr')">FR</button>
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <main class="main">

    <!-- TAB 1: DASHBOARD & SYNC LIVE -->
    <section class="view-section active" id="view-dashboard">
      <div class="page-header">
        <div>
          <div class="page-title" data-i18n="dash_title">Panel de Sincronización PRADO UGR</div>
          <div class="page-subtitle" id="dashFolderSubtitle">Carpeta activa: ~/Documents/UGR_Courses</div>
        </div>
        <div class="row">
          <span class="badge badge-idle" id="syncStatusBadge">🟢 Al día</span>
          <button class="btn btn-secondary" onclick="openFolder('')">📂 <span data-i18n="btn_open_folder">Abrir Carpeta</span></button>
          <button class="btn btn-primary" id="btnSyncNow" onclick="triggerSync()">🔄 <span data-i18n="btn_sync_now">Sincronizar Ahora</span></button>
        </div>
      </div>

      <!-- Progress & Live Log Card -->
      <div class="card">
        <div class="row" style="justify-content:space-between;">
          <div>
            <div style="font-size:14px; font-weight:600;" id="syncStepText">Listo para sincronizar tus asignaturas y correo institucional.</div>
            <div style="font-size:12px; color:var(--text-muted); margin-top:3px;" id="lastSyncLabel">Última sincronización: --:--</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="toggleLogs()" data-i18n="btn_toggle_logs">Ver registro en vivo</button>
        </div>
        <div class="progress-wrap" id="syncProgressWrap">
          <div class="progress-bar-bg"><div class="progress-bar-fill" id="syncProgressBar"></div></div>
        </div>
        <div class="log-box" id="syncLogBox" style="display:none;">Esperando actividad...</div>
      </div>

      <!-- KPI Cards -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label" data-i18n="kpi_courses">Asignaturas Activas</div>
          <div class="kpi-val" id="kpiCourses">0</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label" data-i18n="kpi_files">Archivos Descargados</div>
          <div class="kpi-val" id="kpiFiles">0</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label" data-i18n="kpi_protected">Protegidos Anti-Sobrescritura</div>
          <div class="kpi-val" id="kpiProtected">0</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label" data-i18n="kpi_deadlines">Entregas y Exámenes</div>
          <div class="kpi-val" id="kpiDeadlines">0</div>
        </div>
      </div>

      <!-- Deadlines + Recent Files -->
      <div class="two-col">
        <div class="card">
          <div class="card-title">
            <span>📅 <span data-i18n="card_deadlines">Próximas Entregas y Exámenes</span></span>
            <button class="btn btn-secondary btn-sm" onclick="runCalendarAction('open_ics')">.ics</button>
          </div>
          <div class="item-list" id="deadlinesList"></div>
        </div>

        <div class="card">
          <div class="card-title">
            <span>📥 <span data-i18n="card_recent_files">Últimos Archivos en tu Ordenador</span></span>
          </div>
          <div class="item-list" id="recentFilesList"></div>
        </div>
      </div>
    </section>

    <!-- TAB 2: COURSES & FOLDER ROUTING -->
    <section class="view-section" id="view-courses">
      <div class="page-header">
        <div>
          <div class="page-title" data-i18n="courses_title">Mis Asignaturas y Organización de Carpetas</div>
          <div class="page-subtitle" data-i18n="courses_sub">Elige dónde guardar tus apuntes, el modo de organización y tus subgrupos de prácticas.</div>
        </div>
        <div class="row">
          <button class="btn btn-secondary" onclick="discoverCourses()" id="btnDiscover">🔍 <span data-i18n="btn_discover">Descubrir en PRADO</span></button>
          <button class="btn btn-primary" onclick="saveCourseSettings()">💾 <span data-i18n="btn_save">Guardar Cambios</span></button>
        </div>
      </div>

      <div class="card">
        <div class="two-col">
          <div class="form-group">
            <label class="form-label" data-i18n="lbl_courses_folder">Carpeta Local de Asignaturas</label>
            <div class="row">
              <input type="text" class="input" id="cfgCoursesRoot" placeholder="~/Documents/UGR_Courses">
              <button class="btn btn-secondary" onclick="pickFolderFor('cfgCoursesRoot')">📂 <span data-i18n="btn_browse">Elegir...</span></button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label" data-i18n="lbl_preset_mode">Modo de Organización de Carpetas</label>
            <select class="select" id="cfgPreset">
              <option value="mirror">Mirror (Réplica Oficial de Secciones PRADO)</option>
              <option value="smart">Smart (Clasificación automática Teoría / Prácticas / General)</option>
            </select>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          <span>📚 <span data-i18n="lbl_enrolled_list">Asignaturas Detectadas</span></span>
          <span style="font-size:12px; color:var(--text-muted);" data-i18n="lbl_subgroup_hint">Filtra tu subgrupo (ej. C2, A3) para ignorar otros subgrupos</span>
        </div>
        <div class="item-list" id="coursesManageList" style="max-height:420px;"></div>
      </div>
    </section>

    <!-- TAB 3: UGR MAIL & AUTO-FORWARDING -->
    <section class="view-section" id="view-mail">
      <div class="page-header">
        <div>
          <div class="page-title" data-i18n="mail_title">Buzón Institucional UGR (@correo.ugr.es)</div>
          <div class="page-subtitle" data-i18n="mail_sub">Modo lectura segura (BODY.PEEK) y reenvío automático selectivo a tu correo personal.</div>
        </div>
        <div class="row">
          <select class="select" id="mailFilterMode" onchange="loadMailInbox(false)" style="width:160px;">
            <option value="all">Todos los correos</option>
            <option value="unread">Solo no leídos</option>
            <option value="academic">Solo académicos / PRADO</option>
          </select>
          <input type="text" class="input" id="mailSearchInput" placeholder="Buscar profesor o asunto..." oninput="loadMailInbox(false)" style="width:210px;">
          <button class="btn btn-primary" onclick="loadMailInbox(true)" id="btnRefreshMail">🔄 <span data-i18n="btn_refresh_mail">Actualizar Buzón</span></button>
        </div>
      </div>

      <div class="mail-split">
        <div class="mail-list" id="mailListPane"></div>
        <div class="mail-viewer" id="mailViewerPane">
          <div style="color:var(--text-muted); font-size:13px; margin:auto;" data-i18n="mail_empty_select">Selecciona un correo a la izquierda para leerlo o guardar sus archivos adjuntos.</div>
        </div>
      </div>

      <!-- Auto-Forwarding Card -->
      <div class="card">
        <div class="card-title">
          <span>📨 <span data-i18n="fwd_title">Reenvío Automático Selectivo a tu Correo Personal (@gmail / @icloud)</span></span>
          <button class="btn btn-primary btn-sm" onclick="saveMailForwarding()">💾 <span data-i18n="btn_save_rules">Guardar Reglas</span></button>
        </div>
        <div class="two-col">
          <div>
            <div class="form-group">
              <label class="row" style="cursor:pointer; font-size:13px; font-weight:600;">
                <input type="checkbox" id="cfgFwdEnabled">
                <span data-i18n="lbl_fwd_enable">Activar reenvío automático en cada sincronización</span>
              </label>
            </div>
            <div class="form-group">
              <label class="form-label" data-i18n="lbl_fwd_to">Correo Personal de Destino</label>
              <input type="email" class="input" id="cfgFwdTo" placeholder="tu.correo@gmail.com">
            </div>
            <div class="form-group">
              <label class="form-label" data-i18n="lbl_fwd_mode">Modo de Filtrado</label>
              <select class="select" id="cfgFwdMode">
                <option value="academic">Académico Inteligente (Profesores, Departamentos y Avisos PRADO)</option>
                <option value="custom">Personalizado (Por remitentes o palabras clave)</option>
                <option value="all">Reenviar todos los correos entrantes</option>
              </select>
            </div>
          </div>
          <div>
            <div class="form-group">
              <label class="form-label" data-i18n="lbl_fwd_senders">Filtrar por Profesores / Dominios (separados por coma)</label>
              <input type="text" class="input" id="cfgFwdSenders" placeholder="ej. @decsai.ugr.es, manjavacas@ugr.es, pmesejo@ugr.es">
            </div>
            <div class="form-group">
              <label class="form-label" data-i18n="lbl_fwd_keywords">Filtrar por Palabras Clave en el Asunto (separadas por coma)</label>
              <input type="text" class="input" id="cfgFwdKeywords" placeholder="ej. práctica, examen, nota, tutoría, convocatoria">
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 4: CALENDAR, DAEMON, NOTIFICATIONS & DOCTOR -->
    <section class="view-section" id="view-calendar">
      <div class="page-header">
        <div>
          <div class="page-title" data-i18n="cal_title">Calendario, Automatización y Diagnóstico</div>
          <div class="page-subtitle" data-i18n="cal_sub">Sincroniza tus entregas con Google Calendar o Apple Calendar, configura alertas y verifica el estado del sistema.</div>
        </div>
      </div>

      <div class="two-col">
        <!-- Calendar Card -->
        <div class="card">
          <div class="card-title">📅 <span data-i18n="card_cal_export">Calendario de Entregas y Exámenes</span></div>
          <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:14px;" data-i18n="cal_desc">
            PradoOS genera un archivo estándar RFC-5545 (deadlines.ics) con recordatorios automáticos (3d, 1d y 2h antes para exámenes; 2d, 1d y 3h para entregas) y puede sincronizarlo directamente con Google Calendar.
          </p>
          <div class="row" style="flex-wrap:wrap; gap:10px;">
            <button class="btn btn-primary" onclick="runCalendarAction('open_ics')">📅 <span data-i18n="btn_open_ics">Abrir deadlines.ics</span></button>
            <button class="btn btn-secondary" onclick="runCalendarAction('gcalendar')">📆 <span data-i18n="btn_sync_gcal">Sincronizar Google Calendar</span></button>
            <button class="btn btn-secondary" onclick="runCalendarAction('open_web')">🌐 Google Calendar Web</button>
          </div>
        </div>

        <!-- Daemon & Notifications Card -->
        <div class="card">
          <div class="card-title">⏰ <span data-i18n="card_automation">Sincronización en Segundo Plano y Alertas</span></div>
          <div class="list-row" style="margin-bottom:10px;">
            <div>
              <div class="list-row-title" data-i18n="lbl_daemon_title">Servicio Automático del Sistema (Cada 4 horas)</div>
              <div class="list-row-sub" id="daemonStatusText">Comprobando estado...</div>
            </div>
            <button class="btn btn-secondary btn-sm" id="btnDaemonToggle" onclick="toggleDaemon()">Activar</button>
          </div>

          <div class="list-row">
            <div>
              <div class="list-row-title" data-i18n="lbl_notif_title">Notificaciones Nativas de Escritorio</div>
              <div class="list-row-sub" data-i18n="lbl_notif_sub">Avisos no intrusivos cuando un profesor sube nuevos archivos a PRADO</div>
            </div>
            <div class="row">
              <input type="checkbox" id="cfgNotifEnabled" onchange="toggleNotifications(false)" style="width:18px; height:18px; cursor:pointer;">
              <button class="btn btn-secondary btn-sm" onclick="toggleNotifications(true)">🔔 Test</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Doctor Diagnostic Card -->
      <div class="card">
        <div class="card-title">
          <span>🩺 <span data-i18n="card_doctor">Diagnóstico Integral de Salud (PradoOS Doctor)</span></span>
          <button class="btn btn-primary btn-sm" onclick="runDoctor()" id="btnRunDoctor">🩺 <span data-i18n="btn_run_doctor">Ejecutar Diagnóstico</span></button>
        </div>
        <div class="item-list" id="doctorProbesList">
          <div style="font-size:12.5px; color:var(--text-muted);" data-i18n="doctor_hint">Pulsa "Ejecutar Diagnóstico" para verificar conectividad con PRADO UGR, llavero del sistema, base de datos SQLite y permisos.</div>
        </div>
      </div>
    </section>

  </main>

  <!-- MODAL 1: FIRST-RUN ONBOARDING WIZARD -->
  <div class="modal-backdrop" id="onboardingModal">
    <div class="modal-card">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">
        <div style="font-size:18px; font-weight:700;">🎓 <span data-i18n="onb_title">Configuración de PradoOS</span></div>
        <button class="btn btn-secondary btn-sm" onclick="closeOnboardingModal()">✕</button>
      </div>
      <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:18px;" data-i18n="onb_sub">
        Tus credenciales se guardan cifradas en el Llavero nativo de tu sistema operativo (macOS Keychain / Windows Credential Manager). Jamás se almacenan en texto plano.
      </p>

      <div class="two-col" style="grid-template-columns:1fr 1fr; gap:12px;">
        <div class="form-group">
          <label class="form-label" data-i18n="onb_lang">Idioma / Language</label>
          <select class="select" id="onbLanguage" onchange="setLanguage(this.value)">
            <option value="es">🇪🇸 Español (Predeterminado)</option>
            <option value="en">🇬🇧 English</option>
            <option value="it">🇮🇹 Italiano</option>
            <option value="fr">🇫🇷 Français</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" data-i18n="onb_portal">Portal PRADO UGR</label>
          <select class="select" id="onbPortal">
            <option value="grado">Grado (pradogrado2627.ugr.es)</option>
            <option value="posgrado">Posgrado / Máster (pradoposgrado)</option>
            <option value="ceprud">CEPRUD / Otros</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" data-i18n="onb_email">Correo Institucional UGR</label>
        <input type="email" class="input" id="onbUsername" placeholder="usuario@correo.ugr.es">
      </div>

      <div class="form-group">
        <label class="form-label" data-i18n="onb_password">Contraseña de Acceso Identificado / PRADO</label>
        <input type="password" class="input" id="onbPassword" placeholder="••••••••••••••••">
      </div>

      <div class="form-group">
        <label class="form-label" data-i18n="onb_folder">Carpeta donde se descargarán tus apuntes</label>
        <div class="row">
          <input type="text" class="input" id="onbCoursesRoot" placeholder="~/Documents/UGR_Courses">
          <button class="btn btn-secondary" onclick="pickFolderFor('onbCoursesRoot')">📂 <span data-i18n="btn_browse">Elegir...</span></button>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" data-i18n="lbl_preset_mode">Organización de Carpetas</label>
        <select class="select" id="onbPreset">
          <option value="mirror">Mirror — Réplica exacta de las secciones de cada profesor en PRADO</option>
          <option value="smart">Smart — Clasificación automática en Teoría / Prácticas / General</option>
        </select>
      </div>

      <div class="form-group">
        <label class="row" style="cursor:pointer; font-size:12.5px;">
          <input type="checkbox" id="onbNotifications">
          <span data-i18n="onb_notif">Activar notificaciones de escritorio cuando se descarguen nuevos archivos (Opcional)</span>
        </label>
      </div>

      <div class="row" style="justify-content:flex-end; margin-top:18px;">
        <button class="btn btn-secondary" onclick="closeOnboardingModal()" data-i18n="btn_cancel">Cancelar</button>
        <button class="btn btn-primary" onclick="submitOnboarding()" id="btnSubmitOnboard">🚀 <span data-i18n="onb_submit">Guardar y Sincronizar</span></button>
      </div>
    </div>
  </div>

  <!-- MODAL 2: LIVE 6-DIGIT MFA VERIFICATION -->
  <div class="modal-backdrop" id="mfaModal">
    <div class="modal-card" style="width:430px;">
      <div style="font-size:17px; font-weight:700; margin-bottom:8px;">🔐 Verificación en 2 Pasos (MFA UGR)</div>
      <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:16px;" id="mfaPromptText">
        Introduce el código de 6 dígitos enviado a tu correo institucional @correo.ugr.es. Tu dispositivo quedará verificado durante 30 días.
      </p>
      <div class="form-group">
        <input type="text" maxlength="6" class="input" id="mfaCodeInput" placeholder="123456" style="font-size:22px; text-align:center; letter-spacing:8px; font-weight:700;">
      </div>
      <div class="row" style="justify-content:flex-end; margin-top:14px;">
        <button class="btn btn-primary" onclick="submitMfaCode()" style="width:100%;">✓ Verificar Dispositivo (30 días)</button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div class="toast" id="toastBox"></div>

<script>
const PRADO_TOKEN = "__PRADO_SESSION_TOKEN__";
let appState = null;
let currentLang = "es";
let logsVisible = false;
let onboardingDismissed = false;

const I18N = {
  es: {
    nav_dashboard: "Panel Principal",
    nav_courses: "Mis Asignaturas",
    nav_mail: "Correo UGR y Reenvío",
    nav_calendar: "Calendario y Sistema",
    btn_setup_account: "Configurar Cuenta UGR",
    dash_title: "Panel de Sincronización PRADO UGR",
    btn_open_folder: "Abrir Carpeta",
    btn_sync_now: "Sincronizar Ahora",
    btn_toggle_logs: "Ver registro en vivo",
    kpi_courses: "Asignaturas Activas",
    kpi_files: "Archivos Descargados",
    kpi_protected: "Protegidos Anti-Sobrescritura",
    kpi_deadlines: "Entregas y Exámenes",
    card_deadlines: "Próximas Entregas y Exámenes",
    card_recent_files: "Últimos Archivos en tu Ordenador",
    courses_title: "Mis Asignaturas y Organización de Carpetas",
    courses_sub: "Elige dónde guardar tus apuntes, el modo de organización y tus subgrupos de prácticas.",
    btn_discover: "Descubrir en PRADO",
    btn_save: "Guardar Cambios",
    lbl_courses_folder: "Carpeta Local de Asignaturas",
    btn_browse: "Elegir...",
    lbl_preset_mode: "Modo de Organización de Carpetas",
    lbl_enrolled_list: "Asignaturas Detectadas",
    lbl_subgroup_hint: "Filtra tu subgrupo (ej. C2, A3) para ignorar otros subgrupos",
    mail_title: "Buzón Institucional UGR (@correo.ugr.es)",
    mail_sub: "Modo lectura segura (BODY.PEEK) y reenvío automático selectivo a tu correo personal.",
    btn_refresh_mail: "Actualizar Buzón",
    mail_empty_select: "Selecciona un correo a la izquierda para leerlo o guardar sus archivos adjuntos.",
    fwd_title: "Reenvío Automático Selectivo a tu Correo Personal (@gmail / @icloud)",
    btn_save_rules: "Guardar Reglas",
    lbl_fwd_enable: "Activar reenvío automático en cada sincronización",
    lbl_fwd_to: "Correo Personal de Destino",
    lbl_fwd_mode: "Modo de Filtrado",
    lbl_fwd_senders: "Filtrar por Profesores / Dominios (separados por coma)",
    lbl_fwd_keywords: "Filtrar por Palabras Clave en el Asunto (separadas por coma)",
    cal_title: "Calendario, Automatización y Diagnóstico",
    cal_sub: "Sincroniza tus entregas con Google Calendar o Apple Calendar, configura alertas y verifica el sistema.",
    card_cal_export: "Calendario de Entregas y Exámenes",
    btn_open_ics: "Abrir deadlines.ics",
    btn_sync_gcal: "Sincronizar Google Calendar",
    card_automation: "Sincronización en Segundo Plano y Alertas",
    lbl_daemon_title: "Servicio Automático del Sistema (Cada 4 horas)",
    lbl_notif_title: "Notificaciones Nativas de Escritorio",
    lbl_notif_sub: "Avisos no intrusivos cuando un profesor sube nuevos archivos a PRADO",
    card_doctor: "Diagnóstico Integral de Salud (PradoOS Doctor)",
    btn_run_doctor: "Ejecutar Diagnóstico",
    onb_title: "Configuración de PradoOS",
    onb_email: "Correo Institucional UGR",
    onb_password: "Contraseña de Acceso Identificado / PRADO",
    onb_folder: "Carpeta donde se descargarán tus apuntes",
    onb_submit: "Guardar y Sincronizar",
    btn_cancel: "Cancelar"
  },
  en: {
    nav_dashboard: "Dashboard",
    nav_courses: "My Courses",
    nav_mail: "UGR Mail & Forwarding",
    nav_calendar: "Calendar & System",
    btn_setup_account: "Configure UGR Account",
    dash_title: "PRADO UGR Sync Control Center",
    btn_open_folder: "Open Folder",
    btn_sync_now: "Sync Now",
    btn_toggle_logs: "Toggle live logs",
    kpi_courses: "Active Courses",
    kpi_files: "Downloaded Files",
    kpi_protected: "Conflict-Protected Files",
    kpi_deadlines: "Upcoming Deadlines",
    card_deadlines: "Upcoming Deadlines & Exams",
    card_recent_files: "Recent Files on Your Computer",
    courses_title: "My Courses & Folder Routing",
    courses_sub: "Choose your local notes directory, routing preset, and lab subgroups.",
    btn_discover: "Discover on PRADO",
    btn_save: "Save Changes",
    lbl_courses_folder: "Local Courses Directory",
    btn_browse: "Browse...",
    lbl_preset_mode: "Folder Organization Mode",
    lbl_enrolled_list: "Enrolled Courses",
    lbl_subgroup_hint: "Optional subgroup filter (e.g. C2, A3)",
    mail_title: "UGR Institutional Mailbox (@correo.ugr.es)",
    mail_sub: "Safe non-destructive reading (BODY.PEEK) & selective auto-forwarding to your personal email.",
    btn_refresh_mail: "Refresh Inbox",
    mail_empty_select: "Select an email on the left to read its content or download attachments.",
    fwd_title: "Selective Auto-Forwarding to Personal Email (@gmail / @icloud)",
    btn_save_rules: "Save Rules",
    lbl_fwd_enable: "Enable automatic forwarding on every sync",
    lbl_fwd_to: "Destination Personal Email",
    lbl_fwd_mode: "Filter Mode",
    lbl_fwd_senders: "Filter by Professors / Domains (comma-separated)",
    lbl_fwd_keywords: "Filter by Subject Keywords (comma-separated)",
    cal_title: "Calendar, Automation & System Health",
    cal_sub: "Sync deadlines with Google Calendar or Apple Calendar, manage alerts, and run diagnostics.",
    card_cal_export: "Deadlines & Exams Calendar",
    btn_open_ics: "Open deadlines.ics",
    btn_sync_gcal: "Sync Google Calendar",
    card_automation: "Background Sync & Desktop Alerts",
    lbl_daemon_title: "System Background Service (Every 4 hours)",
    lbl_notif_title: "Native Desktop Notifications",
    lbl_notif_sub: "Non-intrusive alerts when professors upload new materials",
    card_doctor: "System Health Check (PradoOS Doctor)",
    btn_run_doctor: "Run Health Check",
    onb_title: "PradoOS Setup",
    onb_email: "UGR Institutional Email",
    onb_password: "UGR Acceso Identificado / PRADO Password",
    onb_folder: "Destination folder for your course materials",
    onb_submit: "Save & Sync Now",
    btn_cancel: "Cancel"
  },
  it: {
    nav_dashboard: "Pannello Principale",
    nav_courses: "I Miei Corsi",
    nav_mail: "Posta UGR e Inoltro",
    nav_calendar: "Calendario e Sistema",
    btn_setup_account: "Configura Account UGR",
    dash_title: "Centro di Controllo PRADO UGR",
    btn_open_folder: "Apri Cartella",
    btn_sync_now: "Sincronizza Ora",
    btn_toggle_logs: "Mostra log in tempo reale",
    kpi_courses: "Corsi Attivi",
    kpi_files: "File Scaricati",
    kpi_protected: "File Protetti da Sovrascrittura",
    kpi_deadlines: "Scadenze ed Esami",
    card_deadlines: "Prossime Scadenze ed Esami",
    card_recent_files: "Ultimi File sul Computer",
    courses_title: "I Miei Corsi e Gestione Cartelle",
    courses_sub: "Scegli dove salvare gli appunti, la modalità di organizzazione e i sottogruppi di laboratorio.",
    btn_discover: "Scopri su PRADO",
    btn_save: "Salva Modifiche",
    lbl_courses_folder: "Cartella Locale dei Corsi",
    btn_browse: "Sfoglia...",
    lbl_preset_mode: "Modalità Organizzazione Cartelle",
    lbl_enrolled_list: "Insegnamenti Rilevati",
    lbl_subgroup_hint: "Filtra il tuo sottogruppo (es. C2, A3)",
    mail_title: "Casella Istituzionale UGR (@correo.ugr.es)",
    mail_sub: "Lettura sicura (BODY.PEEK) e inoltro automatico selettivo alla tua email personale.",
    btn_refresh_mail: "Aggiorna Posta",
    mail_empty_select: "Seleziona un'email a sinistra per leggerla o scaricare gli allegati.",
    fwd_title: "Inoltro Automatico Selettivo alla Mail Personale (@gmail / @icloud)",
    btn_save_rules: "Salva Regole",
    lbl_fwd_enable: "Attiva inoltro automatico a ogni sincronizzazione",
    lbl_fwd_to: "Email Personale di Destinazione",
    lbl_fwd_mode: "Modalità di Filtro",
    lbl_fwd_senders: "Filtra per Docenti / Domini (separati da virgola)",
    lbl_fwd_keywords: "Filtra per Parole Chiave nell'Oggetto (separate da virgola)",
    cal_title: "Calendario, Automazione e Diagnostica",
    cal_sub: "Sincronizza le scadenze con Google Calendar o Apple Calendar, gestisci notifiche ed esegui Doctor.",
    card_cal_export: "Calendario Scadenze ed Esami",
    btn_open_ics: "Apri deadlines.ics",
    btn_sync_gcal: "Sincronizza Google Calendar",
    card_automation: "Sincronizzazione in Background e Avvisi",
    lbl_daemon_title: "Servizio Automatico di Sistema (Ogni 4 ore)",
    lbl_notif_title: "Notifiche Desktop Native",
    lbl_notif_sub: "Avvisi discreti quando i docenti caricano nuovi materiali su PRADO",
    card_doctor: "Diagnostica Completa (PradoOS Doctor)",
    btn_run_doctor: "Esegui Diagnostica",
    onb_title: "Configurazione PradoOS",
    onb_email: "Email Istituzionale UGR",
    onb_password: "Password Acceso Identificado / PRADO",
    onb_folder: "Cartella dove salvare gli appunti dei corsi",
    onb_submit: "Salva e Sincronizza",
    btn_cancel: "Annulla"
  },
  fr: {
    nav_dashboard: "Tableau de Bord",
    nav_courses: "Mes Cours",
    nav_mail: "Messagerie UGR",
    nav_calendar: "Calendrier et Système",
    btn_setup_account: "Configurer Compte UGR",
    dash_title: "Centre de Contrôle PRADO UGR",
    btn_open_folder: "Ouvrir Dossier",
    btn_sync_now: "Synchroniser",
    btn_toggle_logs: "Afficher le journal en direct",
    kpi_courses: "Cours Actifs",
    kpi_files: "Fichiers Téléchargés",
    kpi_protected: "Fichiers Protégés",
    kpi_deadlines: "Échéances et Examens",
    card_deadlines: "Prochaines Échéances et Examens",
    card_recent_files: "Derniers Fichiers Téléchargés",
    courses_title: "Mes Cours et Organisation des Dossiers",
    courses_sub: "Choisissez le dossier local, le mode de tri et vos sous-groupes de TP.",
    btn_discover: "Découvrir sur PRADO",
    btn_save: "Enregistrer",
    lbl_courses_folder: "Dossier Local des Cours",
    btn_browse: "Parcourir...",
    lbl_preset_mode: "Mode d'Organisation des Dossiers",
    lbl_enrolled_list: "Cours Détectés",
    lbl_subgroup_hint: "Filtrez votre sous-groupe (ex. C2, A3)",
    mail_title: "Messagerie Institutionnelle UGR (@correo.ugr.es)",
    mail_sub: "Lecture sécurisée (BODY.PEEK) et redirection automatique vers votre courriel personnel.",
    btn_refresh_mail: "Actualiser",
    mail_empty_select: "Sélectionnez un courriel à gauche pour le lire ou télécharger ses pièces jointes.",
    fwd_title: "Redirection Automatique vers votre Courriel Personnel (@gmail / @icloud)",
    btn_save_rules: "Enregistrer Règles",
    lbl_fwd_enable: "Activer la redirection automatique à chaque synchronisation",
    lbl_fwd_to: "Courriel Personnel de Destination",
    lbl_fwd_mode: "Mode de Filtrage",
    lbl_fwd_senders: "Filtrer par Professeurs / Domaines (séparés par virgule)",
    lbl_fwd_keywords: "Filtrer par Mots-Clés (séparés par virgule)",
    cal_title: "Calendrier, Automatisation et Diagnostic",
    cal_sub: "Synchronisez vos échéances avec Google Calendar ou Apple Calendar et vérifiez le système.",
    card_cal_export: "Calendrier des Échéances et Examens",
    btn_open_ics: "Ouvrir deadlines.ics",
    btn_sync_gcal: "Synchroniser Google Calendar",
    card_automation: "Synchronisation en Arrière-plan et Alertes",
    lbl_daemon_title: "Service Automatique (Toutes les 4 heures)",
    lbl_notif_title: "Notifications Natives du Bureau",
    lbl_notif_sub: "Alertes lorsque de nouveaux documents sont publiés sur PRADO",
    card_doctor: "Diagnostic du Système (PradoOS Doctor)",
    btn_run_doctor: "Lancer le Diagnostic",
    onb_title: "Configuration de PradoOS",
    onb_email: "Courriel Institutionnel UGR",
    onb_password: "Mot de passe Acceso Identificado / PRADO",
    onb_folder: "Dossier de destination pour vos cours",
    onb_submit: "Enregistrer et Synchroniser",
    btn_cancel: "Annuler"
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
    document.getElementById("view-" + t).classList.toggle("active", t === tab);
    document.getElementById("nav-" + t).classList.toggle("active", t === tab);
  });
  if (tab === "mail") {
    loadMailInbox(false);
  }
}

function toggleLogs() {
  logsVisible = !logsVisible;
  document.getElementById("syncLogBox").style.display = logsVisible ? "block" : "none";
}

async function refreshState() {
  try {
    const st = await apiGet("/api/state");
    appState = st;

    if (st.language && st.language !== currentLang) {
      applyTranslations(st.language);
    }

    document.getElementById("versionLabel").textContent = `v${st.version} • UGR Engine`;
    document.getElementById("sidebarUser").textContent = st.auth.username
      ? `🟢 ${st.auth.username}`
      : "🔴 Sin sesión UGR";
    document.getElementById("dashFolderSubtitle").textContent = `📂 ${st.config.courses_root}`;

    // KPIs
    document.getElementById("kpiCourses").textContent = `${st.stats.active_courses}/${st.stats.total_courses}`;
    document.getElementById("kpiFiles").textContent = st.stats.total_files;
    document.getElementById("kpiProtected").textContent = st.stats.protected_files;
    document.getElementById("kpiDeadlines").textContent = st.deadlines.length;

    // Sync status & progress
    const badge = document.getElementById("syncStatusBadge");
    const progWrap = document.getElementById("syncProgressWrap");
    const progBar = document.getElementById("syncProgressBar");
    const btnSync = document.getElementById("btnSyncNow");

    if (st.sync.status === "syncing" || st.sync.status === "mfa_required") {
      badge.className = "badge badge-syncing";
      badge.textContent = "🟡 Sincronizando...";
      progWrap.classList.add("visible");
      progBar.style.width = `${st.sync.progress_pct || 10}%`;
      btnSync.disabled = true;
      document.getElementById("syncStepText").textContent = st.sync.current_step || "Sincronizando con PRADO UGR...";
    } else if (st.sync.status === "error") {
      badge.className = "badge badge-error";
      badge.textContent = "🔴 Error";
      progWrap.classList.remove("visible");
      btnSync.disabled = false;
      document.getElementById("syncStepText").textContent = st.sync.last_error || "Error durante la sincronización.";
    } else {
      badge.className = "badge badge-idle";
      badge.textContent = "🟢 Al día";
      progWrap.classList.remove("visible");
      btnSync.disabled = false;
      document.getElementById("syncStepText").textContent = st.sync.current_step || "Tus asignaturas están sincronizadas y protegidas.";
    }

    document.getElementById("lastSyncLabel").textContent = `Última sinc.: ${st.sync.last_sync_time || "--:--"}`;

    if (st.sync.logs && st.sync.logs.length > 0) {
      const lb = document.getElementById("syncLogBox");
      lb.textContent = st.sync.logs.join("\n");
      lb.scrollTop = lb.scrollHeight;
    }

    // MFA Modal check
    const mfaModal = document.getElementById("mfaModal");
    if (st.sync.mfa_pending) {
      document.getElementById("mfaPromptText").textContent = st.sync.mfa_prompt || "Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es:";
      mfaModal.classList.add("visible");
    } else {
      mfaModal.classList.remove("visible");
    }

    // First-run onboarding modal check
    if (!st.is_onboarded && !onboardingDismissed) {
      openOnboardingModal(false);
    }

    // Render Deadlines
    renderDeadlines(st.deadlines);
    // Render Recent Files
    renderRecentFiles(st.recent_files);
    // Render Daemon & Notifications
    renderAutomation(st);

    // Populate Courses tab inputs if not currently focused
    if (document.activeElement.id !== "cfgCoursesRoot") {
      document.getElementById("cfgCoursesRoot").value = st.config.courses_root;
    }
    if (document.activeElement.id !== "cfgPreset") {
      document.getElementById("cfgPreset").value = st.config.preset;
    }
    renderCoursesManageList(st.courses);

    // Populate Mail Forwarding inputs if not focused
    if (document.activeElement.id !== "cfgFwdTo") {
      document.getElementById("cfgFwdEnabled").checked = st.config.mail.forward_enabled;
      document.getElementById("cfgFwdTo").value = st.config.mail.forward_to;
      document.getElementById("cfgFwdMode").value = st.config.mail.forward_mode;
      document.getElementById("cfgFwdSenders").value = (st.config.mail.filter_senders || []).join(", ");
      document.getElementById("cfgFwdKeywords").value = (st.config.mail.filter_keywords || []).join(", ");
    }
  } catch (e) {
    console.error("Failed to fetch state:", e);
  }
}

function renderDeadlines(deadlines) {
  const box = document.getElementById("deadlinesList");
  if (!deadlines || deadlines.length === 0) {
    box.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted); padding:10px;">No hay entregas pendientes registradas todavía. Pulsa "Sincronizar Ahora" para extraer las fechas límite de PRADO.</div>`;
    return;
  }
  const nowSec = Date.now() / 1000;
  box.innerHTML = deadlines.map(d => {
    const diffDays = Math.ceil((d.timestamp - nowSec) / 86400);
    let badgeCls = d.kind === "EXAM" ? "badge-error" : "badge-info";
    let tag = d.kind === "EXAM" ? "🚨 EXAMEN" : "📝 ENTREGA";
    let rel = diffDays < 0 ? `Hace ${Math.abs(diffDays)}d` : (diffDays === 0 ? "¡Hoy!" : `En ${diffDays}d`);
    return `
      <div class="list-row">
        <div>
          <div class="list-row-title">${esc(d.title)}</div>
          <div class="list-row-sub">${esc(d.course)} • 🗓️ ${esc(d.due_iso)}</div>
        </div>
        <div class="row">
          <span class="badge ${badgeCls}">${tag} (${rel})</span>
        </div>
      </div>
    `;
  }).join("");
}

function renderRecentFiles(files) {
  const box = document.getElementById("recentFilesList");
  if (!files || files.length === 0) {
    box.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted); padding:10px;">Aún no hay archivos descargados.</div>`;
    return;
  }
  box.innerHTML = files.map(f => {
    const kb = Math.max(1, Math.round((f.file_size || 0) / 1024));
    const statusBadge = f.student_modified
      ? `<span class="badge badge-syncing">🛡️ Protegido</span>`
      : `<span class="badge badge-idle">✓ OK</span>`;
    return `
      <div class="list-row">
        <div style="overflow:hidden;">
          <div class="list-row-title" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">📄 ${esc(f.name)}</div>
          <div class="list-row-sub" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${esc(f.path)} (${kb} KB)</div>
        </div>
        <div class="row" style="flex-shrink:0;">
          ${statusBadge}
          <button class="btn btn-secondary btn-sm" onclick="openFolder(${JSON.stringify(f.path)})">📂</button>
        </div>
      </div>
    `;
  }).join("");
}

function renderCoursesManageList(courses) {
  const box = document.getElementById("coursesManageList");
  if (document.activeElement && document.activeElement.classList.contains("subg-input")) {
    return; // Do not overwrite while typing subgroup
  }
  if (!courses || courses.length === 0) {
    box.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted); padding:10px;">No hay asignaturas descubiertas aún. Pulsa "Descubrir en PRADO" o "Sincronizar Ahora".</div>`;
    return;
  }
  box.innerHTML = courses.map(c => `
    <div class="list-row">
      <div class="row" style="flex:1;">
        <input type="checkbox" class="course-active-chk" data-cid="${c.course_id}" ${c.is_active ? "checked" : ""} style="width:17px; height:17px; cursor:pointer;">
        <div>
          <div class="list-row-title">${esc(c.fullname)}</div>
          <div class="list-row-sub">ID: ${c.course_id} ${c.shortname ? "• " + esc(c.shortname) : ""} ${c.category ? "• " + esc(c.category) : ""}</div>
        </div>
      </div>
      <div class="row">
        <input type="text" class="input subg-input" data-ckey="${esc(c.shortname || c.fullname)}" value="${esc(c.subgroup || "")}" placeholder="Subgrupo (ej. C2)" style="width:145px; padding:6px 10px; font-size:12px;">
        <button class="btn btn-secondary btn-sm" onclick=" triggerCourseSync('${c.course_id}')">🔄</button>
      </div>
    </div>
  `).join("");
}

function renderAutomation(st) {
  const dm = st.daemon || {};
  const dmText = document.getElementById("daemonStatusText");
  const dmBtn = document.getElementById("btnDaemonToggle");
  if (dm.active || dm.installed) {
    dmText.textContent = `🟢 Activo (${dm.backend || "OS Scheduler"} • ${dm.schedule || "cada 4h"})`;
    dmBtn.textContent = "Desactivar";
    dmBtn.dataset.enable = "0";
  } else {
    dmText.textContent = `⚪ No instalado (${dm.backend || "launchd/systemd/schtasks"} disponible)`;
    dmBtn.textContent = "⚡ Activar (Cada 4h)";
    dmBtn.dataset.enable = "1";
  }
  document.getElementById("cfgNotifEnabled").checked = Boolean(st.config.notifications_enabled);
}

// Actions
async function triggerSync() {
  logsVisible = true;
  document.getElementById("syncLogBox").style.display = "block";
  const res = await apiPost("/api/sync/start", {});
  if (res.status === "started") {
    showToast("🔄 Sincronización iniciada en segundo plano...");
    refreshState();
  } else {
    showToast("⚠️ Ya hay una sincronización en curso.");
  }
}

async function triggerCourseSync(courseId) {
  switchTab("dashboard");
  logsVisible = true;
  document.getElementById("syncLogBox").style.display = "block";
  await apiPost("/api/sync/start", { course: String(courseId) });
  showToast("🔄 Sincronizando asignatura seleccionada...");
  refreshState();
}

async function openFolder(relPath) {
  await apiPost("/api/folder/open", { path: relPath || "" });
}

async function pickFolderFor(inputId) {
  const res = await apiPost("/api/folder/pick", {});
  if (res.status === "success" && res.path) {
    document.getElementById(inputId).value = res.path;
  }
}

async function discoverCourses() {
  const btn = document.getElementById("btnDiscover");
  btn.disabled = true;
  showToast("🔍 Conectando con PRADO UGR para descubrir asignaturas...");
  const res = await apiGet("/api/courses/discover");
  btn.disabled = false;
  if (res.status === "success") {
    showToast(`✓ ${res.discovered} asignaturas encontradas en PRADO.`);
    refreshState();
  } else {
    showToast(`❌ Error: ${res.error}`);
  }
}

async function saveCourseSettings() {
  const activeMap = {};
  document.querySelectorAll(".course-active-chk").forEach(chk => {
    activeMap[chk.getAttribute("data-cid")] = chk.checked;
  });
  const subgMap = {};
  document.querySelectorAll(".subg-input").forEach(inp => {
    const k = inp.getAttribute("data-ckey");
    const v = inp.value.trim();
    if (k && v) subgMap[k] = v;
  });
  const res = await apiPost("/api/courses/settings", {
    courses_root: document.getElementById("cfgCoursesRoot").value.trim(),
    preset: document.getElementById("cfgPreset").value,
    active_courses: activeMap,
    subgroups: subgMap
  });
  if (res.status === "success") {
    showToast("💾 Configuración de asignaturas y carpetas guardada.");
    refreshState();
  }
}

// Mail Functions
async function loadMailInbox(refresh) {
  const mode = document.getElementById("mailFilterMode").value;
  const q = document.getElementById("mailSearchInput").value.trim();
  const pane = document.getElementById("mailListPane");
  if (refresh) {
    pane.innerHTML = `<div style="padding:16px; font-size:12.5px; color:var(--text-muted);">🔄 Conectando con correo.ugr.es (IMAP)...</div>`;
  }
  const res = await apiGet(`/api/mail/messages?filter=${encodeURIComponent(mode)}&q=${encodeURIComponent(q)}&refresh=${refresh ? "1" : "0"}`);
  if (res.status !== "success") {
    pane.innerHTML = `<div style="padding:16px; font-size:12.5px; color:var(--red);">❌ ${esc(res.error || "Error al cargar buzón")}</div>`;
    return;
  }
  const msgs = res.messages || [];
  if (msgs.length === 0) {
    pane.innerHTML = `<div style="padding:16px; font-size:12.5px; color:var(--text-muted);">No hay correos que coincidan con el filtro.</div>`;
    return;
  }
  pane.innerHTML = msgs.map(m => `
    <div class="mail-item" onclick="openMailMessage('${esc(m.uid)}', this)">
      <div class="mail-item-subj">
        ${m.is_unread ? "🔵 " : ""}${m.is_academic ? "🎓 " : ""}${esc(m.subject)}
      </div>
      <div class="mail-item-meta">
        <span>${esc(m.sender || m.sender_email)}</span>
        <span>${esc((m.date_str || "").slice(0, 16))}</span>
      </div>
    </div>
  `).join("");
}

async function openMailMessage(uid, el) {
  document.querySelectorAll(".mail-item").forEach(i => i.classList.remove("active"));
  if (el) el.classList.add("active");
  const viewer = document.getElementById("mailViewerPane");
  viewer.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted);">Cargando mensaje...</div>`;
  const res = await apiGet(`/api/mail/message/${encodeURIComponent(uid)}`);
  if (res.status !== "success" || !res.message) {
    viewer.innerHTML = `<div style="color:var(--red); font-size:13px;">❌ ${esc(res.error || "No se pudo abrir el mensaje")}</div>`;
    return;
  }
  const m = res.message;
  const atts = (m.attachments || []).map(a => `
    <button class="btn btn-secondary btn-sm" onclick="downloadAttachment('${esc(m.uid)}', ${a.index})">
      📎 ${esc(a.filename)} (${Math.max(1, Math.round((a.size_bytes || 0)/1024))} KB)
    </button>
  `).join(" ");

  viewer.innerHTML = `
    <div style="font-size:16px; font-weight:700;">${esc(m.subject)}</div>
    <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
      <b>De:</b> ${esc(m.sender)} (${esc(m.sender_email)}) • <b>Fecha:</b> ${esc(m.date_str)}
    </div>
    ${atts ? `<div class="row" style="margin-top:10px; flex-wrap:wrap;">${atts}</div>` : ""}
    <div class="mail-body">${esc(m.body_text || m.snippet || "(Mensaje sin contenido de texto)")}</div>
  `;
}

async function downloadAttachment(uid, index) {
  showToast("📂 Selecciona dónde guardar el archivo adjunto...");
  const res = await apiPost("/api/mail/attachment", { uid: uid, index: index });
  if (res.status === "success") {
    showToast(`✓ Adjunto guardado en: ${res.saved_path}`);
  } else if (res.status !== "cancelled") {
    showToast(`❌ Error: ${res.error}`);
  }
}

async function saveMailForwarding() {
  const res = await apiPost("/api/mail/forwarding", {
    forward_enabled: document.getElementById("cfgFwdEnabled").checked,
    forward_to: document.getElementById("cfgFwdTo").value.trim(),
    forward_mode: document.getElementById("cfgFwdMode").value,
    filter_senders: document.getElementById("cfgFwdSenders").value,
    filter_keywords: document.getElementById("cfgFwdKeywords").value
  });
  if (res.status === "success") {
    showToast("📬 Reglas de reenvío automático guardadas.");
    refreshState();
  }
}

// Calendar, Daemon, Notifications & Doctor
async function runCalendarAction(action) {
  const res = await apiPost("/api/calendar/action", { action: action });
  if (res.status === "success") {
    showToast("✓ Acción de calendario completada.");
  } else {
    showToast(`❌ ${res.error || "Error en calendario"}`);
  }
}

async function toggleDaemon() {
  const btn = document.getElementById("btnDaemonToggle");
  const enable = btn.dataset.enable === "1";
  const res = await apiPost("/api/daemon/toggle", { enable: enable, interval_hours: 4 });
  if (res.status === "success") {
    showToast(enable ? "⏰ Sincronización automática (cada 4h) activada." : "⏰ Sincronización automática desactivada.");
    refreshState();
  } else {
    showToast(`❌ Error: ${res.error}`);
  }
}

async function toggleNotifications(testNow) {
  const enabled = document.getElementById("cfgNotifEnabled").checked;
  await apiPost("/api/notifications/toggle", { enabled: enabled, test: Boolean(testNow) });
  showToast(testNow ? "🔔 Notificación de prueba enviada." : (enabled ? "🔔 Notificaciones activadas." : "🔕 Notificaciones desactivadas."));
}

async function runDoctor() {
  const box = document.getElementById("doctorProbesList");
  box.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted);">🩺 Ejecutando las 9 sondas de diagnóstico...</div>`;
  const res = await apiGet("/api/doctor");
  if (!res.probes) {
    box.innerHTML = `<div style="color:var(--red);">Error al ejecutar diagnóstico.</div>`;
    return;
  }
  box.innerHTML = res.probes.map(p => {
    const cls = p.status === "OK" ? "badge-idle" : (p.status === "WARN" ? "badge-syncing" : "badge-error");
    return `
      <div class="list-row">
        <div>
          <div class="list-row-title">${esc(p.name)}</div>
          <div class="list-row-sub">${esc(p.message)} ${p.remediation ? "• 💡 " + esc(p.remediation) : ""}</div>
        </div>
        <span class="badge ${cls}">${esc(p.status)}</span>
      </div>
    `;
  }).join("");
}

// Onboarding & MFA Modals
function openOnboardingModal(manual) {
  if (appState) {
    document.getElementById("onbLanguage").value = appState.language || "es";
    document.getElementById("onbPortal").value = appState.auth.portal || "grado";
    document.getElementById("onbUsername").value = appState.auth.username || "";
    document.getElementById("onbCoursesRoot").value = appState.config.courses_root || "";
    document.getElementById("onbPreset").value = appState.config.preset || "mirror";
    document.getElementById("onbNotifications").checked = Boolean(appState.config.notifications_enabled);
  }
  document.getElementById("onboardingModal").classList.add("visible");
}

function closeOnboardingModal() {
  onboardingDismissed = true;
  document.getElementById("onboardingModal").classList.remove("visible");
}

async function submitOnboarding() {
  const payload = {
    language: document.getElementById("onbLanguage").value,
    portal: document.getElementById("onbPortal").value,
    username: document.getElementById("onbUsername").value.trim(),
    password: document.getElementById("onbPassword").value,
    courses_root: document.getElementById("onbCoursesRoot").value.trim(),
    preset: document.getElementById("onbPreset").value,
    notifications_enabled: document.getElementById("onbNotifications").checked,
    start_sync: true
  };
  const res = await apiPost("/api/onboard", payload);
  if (res.status === "success") {
    closeOnboardingModal();
    logsVisible = true;
    document.getElementById("syncLogBox").style.display = "block";
    showToast("🚀 Cuenta guardada en el Llavero. Iniciando primera sincronización...");
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
    showToast("✓ Código MFA enviado. Validando sesión por 30 días...");
    refreshState();
  } else {
    showToast(`❌ ${res.error}`);
  }
}

// Initial load & live polling (every 1.5s)
refreshState();
setInterval(refreshState, 1500);
</script>
</body>
</html>
"""
