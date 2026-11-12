"""
Internationalization (i18n) module for PradoOS (`prado-os`).

Supported languages:
- 'es': Español (Default / UGR Primary)
- 'en': English (International / Erasmus)
- 'it': Italiano (Primary Erasmus community at UGR ~35%)
- 'fr': Français (Second largest Western European Erasmus community ~15%)
"""

from __future__ import annotations

from typing import Any, Dict

SUPPORTED_LANGUAGES = ("es", "en", "it", "fr")
DEFAULT_LANGUAGE = "es"

LANGUAGE_NAMES = {
    "es": "Español (Predeterminado)",
    "en": "English",
    "it": "Italiano",
    "fr": "Français",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # -------------------------------------------------------------------------
    # Main Interactive Menu (CLI)
    # -------------------------------------------------------------------------
    "menu_header": {
        "es": "🎓 PradoOS — Motor Académico PRADO UGR",
        "en": "🎓 PradoOS — PRADO UGR Academic Engine",
        "it": "🎓 PradoOS — Motore Accademico PRADO UGR",
        "fr": "🎓 PradoOS — Moteur Académique PRADO UGR",
    },
    "menu_opt_1": {
        "es": "[1] 🔄 Sincronizar Asignaturas y Correo Ahora",
        "en": "[1] 🔄 Sync Courses and Mail Now",
        "it": "[1] 🔄 Sincronizza Insegnamenti e Posta Ora",
        "fr": "[1] 🔄 Synchroniser Cours et Courrier Maintenant",
    },
    "menu_opt_2": {
        "es": "[2] 📬 Lector de Correo UGR y Reenvío Automático",
        "en": "[2] 📬 Read UGR Mail & Auto-Forwarding Rules",
        "it": "[2] 📬 Lettore Posta UGR e Regole Inoltro Automatico",
        "fr": "[2] 📬 Lecteur Courriel UGR et Règles de Redirection",
    },
    "menu_opt_3": {
        "es": "[3] 🔧 Configuración Inicial / Cambiar Ajustes (Wizard)",
        "en": "[3] 🔧 First-Time Setup / Change Settings (Wizard)",
        "it": "[3] 🔧 Configurazione Iniziale / Modifica Impostazioni (Wizard)",
        "fr": "[3] 🔧 Configuration Initiale / Modifier Paramètres (Assistant)",
    },
    "menu_opt_4": {
        "es": "[4] 📚 Descubrir y Listar Asignaturas Matriculadas",
        "en": "[4] 📚 Discover & List Enrolled Courses",
        "it": "[4] 📚 Scopri ed Elenca Insegnamenti Iscritti",
        "fr": "[4] 📚 Découvrir et Lister les Cours Inscrits",
    },
    "menu_opt_5": {
        "es": "[5] 🩺 Diagnóstico del Sistema (Doctor)",
        "en": "[5] 🩺 Run System Health Check (Doctor)",
        "it": "[5] 🩺 Diagnostica del Sistema (Doctor)",
        "fr": "[5] 🩺 Diagnostic du Système (Doctor)",
    },
    "menu_opt_6": {
        "es": "[6] ⏰ Activar Sincronización Automática (Cada 4h)",
        "en": "[6] ⏰ Enable Automatic Background Sync (Every 4h)",
        "it": "[6] ⏰ Attiva Sincronizzazione Automatica (Ogni 4h)",
        "fr": "[6] ⏰ Activer la Synchronisation Automatique (Toutes les 4h)",
    },
    "menu_opt_7": {
        "es": "[7] 📅 Sincronizar Entregas con Google Calendar",
        "en": "[7] 📅 Sync Deadlines to Google Calendar",
        "it": "[7] 📅 Sincronizza Scadenze con Google Calendar",
        "fr": "[7] 📅 Synchroniser les Échéances avec Google Calendar",
    },
    "menu_opt_8": {
        "es": "[8] ⭐ Dar una Estrella a prado-os en GitHub",
        "en": "[8] ⭐ Star prado-os on GitHub",
        "it": "[8] ⭐ Lascia una Stella a prado-os su GitHub",
        "fr": "[8] ⭐ Laisser une Étoile à prado-os sur GitHub",
    },
    "menu_opt_0": {
        "es": "[0] 🚪 Salir",
        "en": "[0] 🚪 Exit",
        "it": "[0] 🚪 Esci",
        "fr": "[0] 🚪 Quitter",
    },
    "menu_prompt": {
        "es": "\nElige una opción [1-8, 0 para salir]: ",
        "en": "\nSelect an option [1-8, 0 to exit]: ",
        "it": "\nScegli un'opzione [1-8, 0 per uscire]: ",
        "fr": "\nChoisissez une option [1-8, 0 pour quitter] : ",
    },
    "invalid_option": {
        "es": "Opción no válida. Inténtalo de nuevo.",
        "en": "Invalid option. Please try again.",
        "it": "Opzione non valida. Riprova.",
        "fr": "Option non valide. Veuillez réessayer.",
    },

    # -------------------------------------------------------------------------
    # Onboarding Wizard Strings
    # -------------------------------------------------------------------------
    "wizard_welcome_banner": {
        "es": "🎓 ASISTENTE DE CONFIGURACIÓN DE PRADOOS",
        "en": "🎓 PRADOOS INITIAL SETUP WIZARD",
        "it": "🎓 ASSISTENTE DI CONFIGURAZIONE DI PRADOOS",
        "fr": "🎓 ASSISTANT DE CONFIGURATION DE PRADOOS",
    },
    "wizard_welcome_sub": {
        "es": "Configuración rápida en 2 sencillos pasos.",
        "en": "Quick setup in 2 simple steps.",
        "it": "Configurazione rapida in 2 semplici passaggi.",
        "fr": "Configuration rapide en 2 étapes simples.",
    },
    "wizard_q1_lang": {
        "es": "¿Qué idioma prefieres usar?",
        "en": "Which language do you prefer to use?",
        "it": "Quale lingua preferisci usare?",
        "fr": "Quelle langue préférez-vous utiliser ?",
    },
    "wizard_q1_folder": {
        "es": "¿Dónde te gustaría guardar las carpetas de tus asignaturas?",
        "en": "Where would you like to keep your university courses folder?",
        "it": "Dove vorresti salvare le cartelle dei tuoi insegnamenti?",
        "fr": "Où souhaitez-vous enregistrer les dossiers de vos cours ?",
    },
    "wizard_q1_folder_help": {
        "es": "Introduce la ruta, pulsa [Enter] para usar la ruta por defecto o pulsa [G] para abrir el selector gráfico nativo.",
        "en": "Enter path, press [Enter] for default, or press [G] to open the native graphical folder picker.",
        "it": "Inserisci il percorso, premi [Invio] per il default o [G] per aprire il selettore grafico nativo.",
        "fr": "Entrez le chemin, appuyez sur [Entrée] par défaut ou [G] pour ouvrir le sélecteur graphique.",
    },
    "wizard_q2_schedule": {
        "es": "¿Deseas activar la sincronización automática en segundo plano (cada 4 horas)?",
        "en": "Would you like to enable automatic background sync (every 4 hours)?",
        "it": "Vuoi attivare la sincronizzazione automatica in background (ogni 4 ore)?",
        "fr": "Souhaitez-vous activer la synchronisation automatique en arrière-plan (toutes les 4 heures) ?",
    },
    "wizard_q2_schedule_sub": {
        "es": "Sincronizará materiales y revisará tu correo UGR periódicamente sin que tengas que abrir el terminal.",
        "en": "This will sync materials and check your UGR email periodically without opening the terminal.",
        "it": "Sincronizzerà materiali e controllerà la posta UGR periodicamente senza dover aprire il terminale.",
        "fr": "Cela synchronisera les cours et vérifiera vos courriels UGR sans ouvrir le terminal.",
    },
    "wizard_preset_prompt": {
        "es": "¿Qué estilo de organización prefieres?",
        "en": "Which organization preset do you prefer?",
        "it": "Quale stile di organizzazione preferisci?",
        "fr": "Quel style d'organisation préférez-vous ?",
    },
    "wizard_preset_mirror": {
        "es": "[1] Mirror (Recomendado): mantiene los nombres oficiales de PRADO y la estructura de los profesores.",
        "en": "[1] Mirror (Recommended): keeps official PRADO course names and professor section layout.",
        "it": "[1] Mirror (Consigliato): mantiene i nomi ufficiali di PRADO e la struttura dei docenti.",
        "fr": "[1] Mirror (Recommandé) : conserve les noms officiels de PRADO et la structure des professeurs.",
    },
    "wizard_preset_smart": {
        "es": "[2] Smart / IA: organiza automáticamente en Teoria/, Practicas/ y General/ (ideal para asistentes IA).",
        "en": "[2] Smart / AI: auto-sorts into Theory/, Labs/, and General/ (ideal for AI assistants).",
        "it": "[2] Smart / IA: organizza automaticamente in Teoria/, Pratiche/ e Generale/ (ideale per agenti IA).",
        "fr": "[2] Smart / IA : classe automatiquement en Théorie/, Travaux Pratiques/ et Général/.",
    },
    "wizard_summary_ready": {
        "es": "Configuración lista. Guardando credenciales y preparando la primera sincronización...",
        "en": "Setup ready. Saving credentials and preparing initial sync...",
        "it": "Configurazione completata. Salvataggio credenziali e avvio della prima sincronizzazione...",
        "fr": "Configuration prête. Enregistrement des identifiants et lancement de la première synchronisation...",
    },
    "wizard_login_prompt": {
        "es": "Iniciando sesión segura en PRADO UGR...",
        "en": "Starting secure login to PRADO UGR...",
        "it": "Avvio accesso sicuro a PRADO UGR...",
        "fr": "Connexion sécurisée à PRADO UGR en cours...",
    },
    "wizard_login_success": {
        "es": "¡Sesión iniciada con éxito! Dispositivo de confianza activado por 30 días.",
        "en": "Login successful! 30-day device trust token activated.",
        "it": "Accesso riuscito! Token dispositivo attendibile attivato per 30 giorni.",
        "fr": "Connexion réussie ! Jeton de confiance 30 jours activé.",
    },

    # -------------------------------------------------------------------------
    # GitHub Star Dialog
    # -------------------------------------------------------------------------
    "star_prompt": {
        "es": "¿Te gustaría dejar una estrella al proyecto prado-os en GitHub para apoyar su desarrollo?",
        "en": "Would you like to leave a star on GitHub to support prado-os development?",
        "it": "Ti andrebbe di lasciare una stella a prado-os su GitHub per supportare lo sviluppo?",
        "fr": "Souhaitez-vous laisser une étoile sur GitHub pour soutenir le développement de prado-os ?",
    },
    "star_success": {
        "es": "¡Muchas gracias por tu apoyo con una estrella en GitHub!",
        "en": "Thank you so much for starring the repository on GitHub!",
        "it": "Grazie mille per il supporto con una stella su GitHub!",
        "fr": "Merci beaucoup pour votre soutien avec une étoile sur GitHub !",
    },
    "star_skipped": {
        "es": "Sin problema. ¡Esperamos que PradoOS te sea de gran utilidad!",
        "en": "No problem! We hope PradoOS saves you plenty of time this semester!",
        "it": "Nessun problema. Buono studio e buon semestre con PradoOS!",
        "fr": "Pas de souci ! Nous espérons que PradoOS vous fera gagner un temps précieux ce semestre !",
    },

    # -------------------------------------------------------------------------
    # UGR Mail TUI Reader
    # -------------------------------------------------------------------------
    "mail_title": {
        "es": "📬 PradoOS — Lector de Correo Institucional UGR (@correo.ugr.es)",
        "en": "📬 PradoOS — UGR Institutional Mail Reader (@correo.ugr.es)",
        "it": "📬 PradoOS — Lettore Posta Istituzionale UGR (@correo.ugr.es)",
        "fr": "📬 PradoOS — Lecteur de Courriel Institutionnel UGR (@correo.ugr.es)",
    },
    "mail_controls": {
        "es": "Controles: [1-N] Abrir | [F] Filtro | [R] Reglas de Reenvío | [A] Descargar Adjuntos | [Q] Salir",
        "en": "Controls: [1-N] Open | [F] Filter | [R] Forwarding Rules | [A] Download Attachments | [Q] Exit",
        "it": "Controlli: [1-N] Apri | [F] Filtro | [R] Regole Inoltro | [A] Salva Allegati | [Q] Esci",
        "fr": "Contrôles : [1-N] Ouvrir | [F] Filtrer | [R] Règles de Redirection | [A] Pièces Jointes | [Q] Quitter",
    },
    "mail_empty": {
        "es": "No hay correos para mostrar en esta vista.",
        "en": "No emails found in this view.",
        "it": "Nessuna email presente in questa visualizzazione.",
        "fr": "Aucun courriel à afficher dans cette vue.",
    },
    "mail_filter_active": {
        "es": "Filtro activo: {filter_name}",
        "en": "Active filter: {filter_name}",
        "it": "Filtro attivo: {filter_name}",
        "fr": "Filtre actif : {filter_name}",
    },
    "mail_forwarding_rules_title": {
        "es": "Configuración de Reglas de Auto-Reenvío",
        "en": "Auto-Forwarding Rules Configuration",
        "it": "Configurazione Regole di Inoltro Automatico",
        "fr": "Configuration des Règles de Redirection Automatique",
    },
    "mail_attachments_saved": {
        "es": "Adjunto guardado en: {dest}",
        "en": "Attachment saved to: {dest}",
        "it": "Allegato salvato in: {dest}",
        "fr": "Pièce jointe enregistrée dans : {dest}",
    },

    # -------------------------------------------------------------------------
    # Sync & Common Feedback
    # -------------------------------------------------------------------------
    "sync_starting": {
        "es": "Iniciando sincronización de asignaturas...",
        "en": "Starting course synchronization...",
        "it": "Avvio sincronizzazione insegnamenti...",
        "fr": "Démarrage de la synchronisation des cours...",
    },
    "sync_completed": {
        "es": "Sincronización completada con éxito.",
        "en": "Synchronization completed successfully.",
        "it": "Sincronizzazione completata con successo.",
        "fr": "Synchronisation terminée avec succès.",
    },
    "doctor_healthy": {
        "es": "Diagnóstico completado: todos los sistemas funcionan correctamente.",
        "en": "Health check passed: all systems operating normally.",
        "it": "Diagnostica completata: tutti i sistemi funzionano correttamente.",
        "fr": "Diagnostic réussi : tous les systèmes fonctionnent correctement.",
    },

    # -------------------------------------------------------------------------
    # System Tray / Menu Bar App (GUI)
    # -------------------------------------------------------------------------
    "tray_open_control_center": {
        "es": "🖥️ Abrir Centro de Control PradoOS",
        "en": "🖥️ Open PradoOS Control Center",
        "it": "🖥️ Apri Centro di Controllo PradoOS",
        "fr": "🖥️ Ouvrir le Centre de Contrôle PradoOS",
    },
    "tray_status_idle": {
        "es": "🟢 PradoOS: Al día",
        "en": "🟢 PradoOS: Up to date",
        "it": "🟢 PradoOS: Aggiornato",
        "fr": "🟢 PradoOS: À jour",
    },
    "tray_status_syncing": {
        "es": "🟡 PradoOS: Sincronizando...",
        "en": "🟡 PradoOS: Syncing...",
        "it": "🟡 PradoOS: Sincronizzazione in corso...",
        "fr": "🟡 PradoOS: Synchronisation en cours...",
    },
    "tray_status_error": {
        "es": "🔴 PradoOS: Error / Iniciar Sesión",
        "en": "🔴 PradoOS: Error / Login Required",
        "it": "🔴 PradoOS: Errore / Login Richiesto",
        "fr": "🔴 PradoOS: Erreur / Connexion Requise",
    },
    "tray_last_sync": {
        "es": "Última sinc.: {time}",
        "en": "Last sync: {time}",
        "it": "Ultima sinc.: {time}",
        "fr": "Dernière sync : {time}",
    },
    "tray_sync_now": {
        "es": "🔄 Sincronizar Ahora",
        "en": "🔄 Sync Now",
        "it": "🔄 Sincronizza Ora",
        "fr": "🔄 Synchroniser Maintenant",
    },
    "tray_open_folder": {
        "es": "📂 Abrir Carpeta de Apuntes",
        "en": "📂 Open Courses Folder",
        "it": "📂 Apri Cartella Appunti",
        "fr": "📂 Ouvrir Dossier des Cours",
    },
    "tray_courses_menu": {
        "es": "📚 Mis Asignaturas ({count})",
        "en": "📚 My Courses ({count})",
        "it": "📚 I Miei Corsi ({count})",
        "fr": "📚 Mes Matières ({count})",
    },
    "tray_courses_empty": {
        "es": "(Sincroniza para detectar tus asignaturas)",
        "en": "(Sync to detect your enrolled courses)",
        "it": "(Sincronizza per rilevare i tuoi corsi)",
        "fr": "(Synchronisez pour détecter vos cours)",
    },
    "tray_preset_mirror": {
        "es": "Modo Oficial PRADO (Mirror)",
        "en": "Official PRADO Structure (Mirror)",
        "it": "Struttura Ufficiale PRADO (Mirror)",
        "fr": "Structure Officielle PRADO (Mirror)",
    },
    "tray_preset_smart": {
        "es": "Modo IA: Teoría y Prácticas (Smart)",
        "en": "AI Mode: Theory & Labs (Smart)",
        "it": "Modalità IA: Teoria e Pratiche (Smart)",
        "fr": "Mode IA : Théorie et TP (Smart)",
    },
    "tray_change_folder": {
        "es": "📁 Cambiar Carpeta de Destino...",
        "en": "📁 Change Destination Folder...",
        "it": "📁 Cambia Cartella di Destinazione...",
        "fr": "📁 Changer le Dossier de Destination...",
    },
    "tray_deadlines_menu": {
        "es": "📅 Próximas Entregas ({count})",
        "en": "📅 Upcoming Deadlines ({count})",
        "it": "📅 Prossime Scadenze ({count})",
        "fr": "📅 Prochaines Échéances ({count})",
    },
    "tray_deadlines_empty": {
        "es": "(Sin entregas próximas pendientes)",
        "en": "(No upcoming deadlines)",
        "it": "(Nessuna scadenza imminente)",
        "fr": "(Aucune échéance à venir)",
    },
    "tray_sync_gcal": {
        "es": "📆 Sincronizar con Google Calendar",
        "en": "📆 Sync with Google Calendar",
        "it": "📆 Sincronizza con Google Calendar",
        "fr": "📆 Synchroniser avec Google Calendar",
    },
    "tray_open_ics": {
        "es": "📅 Abrir archivo deadlines.ics",
        "en": "📅 Open deadlines.ics file",
        "it": "📅 Apri file deadlines.ics",
        "fr": "📅 Ouvrir le fichier deadlines.ics",
    },
    "tray_mail_menu": {
        "es": "📬 Correo UGR (@correo.ugr.es)",
        "en": "📬 UGR Mail (@correo.ugr.es)",
        "it": "📬 Posta UGR (@correo.ugr.es)",
        "fr": "📬 Courriel UGR (@correo.ugr.es)",
    },
    "tray_mail_forward_toggle": {
        "es": "Auto-Reenvío a correo personal {target}",
        "en": "Auto-Forward to personal email {target}",
        "it": "Inoltro automatico a email personale {target}",
        "fr": "Redirection auto vers courriel personnel {target}",
    },
    "tray_mail_check_now": {
        "es": "🔄 Comprobar y reenviar correos ahora",
        "en": "🔄 Check and forward emails now",
        "it": "🔄 Controlla e inoltra email ora",
        "fr": "🔄 Vérifier et rediriger maintenant",
    },
    "tray_lang_menu": {
        "es": "🌐 Idioma / Language",
        "en": "🌐 Language / Idioma",
        "it": "🌐 Lingua / Language",
        "fr": "🌐 Langue / Language",
    },
    "tray_doctor": {
        "es": "🛡️ Diagnóstico del Sistema (Doctor)",
        "en": "🛡️ System Diagnostics (Doctor)",
        "it": "🛡️ Diagnostica di Sistema (Doctor)",
        "fr": "🛡️ Diagnostic du Système (Doctor)",
    },
    "tray_open_calendar": {
        "es": "📅 Abrir Calendario de Entregas",
        "en": "📅 Open Deadlines Calendar",
        "it": "📅 Apri Calendario Scadenze",
        "fr": "📅 Ouvrir Calendrier des Échéances",
    },
    "tray_open_mail": {
        "es": "📬 Abrir Correo UGR",
        "en": "📬 Open UGR Webmail",
        "it": "📬 Apri Webmail UGR",
        "fr": "📬 Ouvrir Messagerie UGR",
    },
    "tray_settings": {
        "es": "⚙️ Configuración / Iniciar Sesión",
        "en": "⚙️ Settings / Login",
        "it": "⚙️ Impostazioni / Login",
        "fr": "⚙️ Paramètres / Connexion",
    },
    "tray_notifications": {
        "es": "🔔 Notificaciones de Escritorio",
        "en": "🔔 Desktop Notifications",
        "it": "🔔 Notifiche Desktop",
        "fr": "🔔 Notifications du Bureau",
    },
    "tray_auto_sync": {
        "es": "⏰ Sincronización Automática (Segundo Plano)",
        "en": "⏰ Auto-Sync in Background",
        "it": "⏰ Sincronizzazione Automatica in Background",
        "fr": "⏰ Synchronisation Automatique en Arrière-plan",
    },
    "tray_github": {
        "es": "⭐ PradoOS en GitHub",
        "en": "⭐ PradoOS on GitHub",
        "it": "⭐ PradoOS su GitHub",
        "fr": "⭐ PradoOS sur GitHub",
    },
    "tray_quit": {
        "es": "❌ Salir de PradoOS",
        "en": "❌ Quit PradoOS",
        "it": "❌ Esci da PradoOS",
        "fr": "❌ Quitter PradoOS",
    },
    "tray_sync_success_notification": {
        "es": "Sincronización completada con éxito.",
        "en": "Sync completed successfully.",
        "it": "Sincronizzazione completata con successo.",
        "fr": "Synchronisation terminée avec succès.",
    },
    "tray_sync_error_notification": {
        "es": "Error en sincronización: {error}",
        "en": "Sync error: {error}",
        "it": "Errore di sincronizzazione: {error}",
        "fr": "Erreur de synchronisation : {error}",
    },
    "tray_credentials_saved": {
        "es": "Credenciales UGR guardadas de forma segura en el llavero del sistema.",
        "en": "UGR credentials securely stored in OS Keychain/Vault.",
        "it": "Credenziali UGR salvate in sicurezza nel portachiavi di sistema.",
        "fr": "Identifiants UGR enregistrés en toute sécurité dans le trousseau.",
    },
    "tray_login_cancelled": {
        "es": "Inicio de sesión cancelado.",
        "en": "Login cancelled.",
        "it": "Login annullato.",
        "fr": "Connexion annulée.",
    },
    "tray_window_title": {
        "es": "PradoOS — Configuración UGR",
        "en": "PradoOS — UGR Setup",
        "it": "PradoOS — Configurazione UGR",
        "fr": "PradoOS — Configuration UGR",
    },
    "tray_deadline_overdue": {
        "es": "vencido",
        "en": "overdue",
        "it": "scaduto",
        "fr": "expiré",
    },
    "tray_open_gcal_web": {
        "es": "🌐 Google Calendar Web",
        "en": "🌐 Google Calendar Web",
        "it": "🌐 Google Calendar Web",
        "fr": "🌐 Google Calendar Web",
    },
    "tray_gcal_synced": {
        "es": "Entregas sincronizadas con Google Calendar.",
        "en": "Deadlines synced with Google Calendar.",
        "it": "Scadenze sincronizzate con Google Calendar.",
        "fr": "Échéances synchronisées avec Google Calendar.",
    },
    "tray_gcal_error": {
        "es": "Google Calendar: {error}",
        "en": "Google Calendar: {error}",
        "it": "Google Calendar: {error}",
        "fr": "Google Calendar : {error}",
    },
    "tray_mail_unread_title": {
        "es": "PradoOS — Correo UGR",
        "en": "PradoOS — UGR Mail",
        "it": "PradoOS — Posta UGR",
        "fr": "PradoOS — Courriel UGR",
    },
    "tray_mail_unread_msg": {
        "es": "{count} correo(s) sin leer en @correo.ugr.es.",
        "en": "{count} unread email(s) in @correo.ugr.es.",
        "it": "{count} email non lette in @correo.ugr.es.",
        "fr": "{count} courriel(s) non lu(s) dans @correo.ugr.es.",
    },
    "tray_doctor_result": {
        "es": "Diagnóstico completado: {ok}/{total} sondas OK.",
        "en": "Diagnostics complete: {ok}/{total} probes OK.",
        "it": "Diagnostica completata: {ok}/{total} controlli OK.",
        "fr": "Diagnostic terminé : {ok}/{total} sondes OK.",
    },
}


def normalize_language(lang_code: str | None) -> str:
    """Normalize language code to one of ('es', 'en', 'it', 'fr'), defaulting to 'es'."""
    if not lang_code:
        return DEFAULT_LANGUAGE
    code = lang_code.strip().lower()
    if code in ("es", "spanish", "español", "esp"):
        return "es"
    if code in ("en", "english", "eng", "inglés", "ingles"):
        return "en"
    if code in ("it", "italian", "italiano", "ita"):
        return "it"
    if code in ("fr", "french", "français", "francais", "fra"):
        return "fr"
    return DEFAULT_LANGUAGE


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """
    Translate key for given language with fallback hierarchy:
    lang -> 'es' -> 'en' -> key itself.
    """
    normalized = normalize_language(lang)
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key

    text = entry.get(normalized) or entry.get("es") or entry.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
