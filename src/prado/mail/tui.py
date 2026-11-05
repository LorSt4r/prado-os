"""
Interactive TUI Mail Reader, Manual Filter Manager, and Auto-Forwarding Configurator for PradoOS.

Displays the full UGR inbox unfiltered by default (like Webmail), while placing
manual filter controls (`[F]`) and auto-forwarding rules (`[R]`) right at the top.
When saving email attachments, always opens the native OS graphical folder picker
(`prompt_folder_picker_gui`) so the user chooses where to save each file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from prado.config import (
    PradoConfig,
    load_config,
    prompt_folder_picker_gui,
    save_config,
)
from prado.mail.client import (
    MailAttachment,
    MailMessage,
    UgrMailClient,
    load_mail_cache,
    matches_mail_filter,
    sanitize_attachment_filename,
)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024.0:.1f} KB"
    return f"{size_bytes / (1024.0 * 1024.0):.2f} MB"


def save_attachment_to_folder(att: MailAttachment, target_dir: Path) -> Path:
    """
    Saves an attachment payload into `target_dir` without overwriting existing files.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_attachment_filename(att.filename)
    dest = target_dir / safe_name
    if dest.exists():
        stem = dest.stem
        ext = dest.suffix
        counter = 1
        while dest.exists():
            dest = target_dir / f"{stem}_{counter}{ext}"
            counter += 1
    dest.write_bytes(att.payload or b"")
    return dest


def configure_mail_filters_interactive(
    cfg: PradoConfig,
    current_view_mode: str = "all",
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> str:
    """
    Interactive menu (`[F]`) to switch the inbox view filter or edit manual professor/keyword filters.
    Returns the newly selected `view_mode` ('all', 'unread', 'academic', or 'custom').
    """
    is_en = cfg.language == "en"
    while True:
        senders_str = ", ".join(cfg.mail.filter_senders) if cfg.mail.filter_senders else ("(none)" if is_en else "(ninguno)")
        keywords_str = ", ".join(cfg.mail.filter_keywords) if cfg.mail.filter_keywords else ("(none)" if is_en else "(ninguna)")

        print_fn("\n" + "─" * 68)
        if is_en:
            print_fn("🔍 FILTER & VIEW SETTINGS (UGR Mail)")
            print_fn(f"   • Current View Mode       : {current_view_mode.upper()}")
            print_fn(f"   • Saved Professor/Senders : {senders_str}")
            print_fn(f"   • Saved Subject Keywords  : {keywords_str}")
            print_fn("─" * 68)
            print_fn("  [1] 📋 Show ALL Inbox (No filters — exact Webmail view) [Default]")
            print_fn("  [2] ●  Show Only UNREAD Emails")
            print_fn("  [3] 🎓 Show Only Academic / UGR Professors & PRADO (hides Rectorado spam)")
            print_fn("  [4] 🎯 Show Only My Custom Filters (Specific Professors / Keywords)")
            print_fn("  [5] ➕ Add Professor Email / Domain Filter (e.g. manjavacas@ugr.es, @decsai.ugr.es)")
            print_fn("  [6] 🏷️  Add Subject / Course Keyword Filter (e.g. Examen, Nota, Práctica, ED)")
            print_fn("  [7] 🗑️  Clear All Manual Filters")
            print_fn("  [0] ↩️  Back to Inbox")
            choice = input_fn("\nSelect an option [1-7, 0 to return]: ").strip()
        else:
            print_fn("🔍 FILTROS DE VISTA Y FILTROS MANUALES (Correo UGR)")
            print_fn(f"   • Vista actual            : {current_view_mode.upper()}")
            print_fn(f"   • Profesores / Remitentes : {senders_str}")
            print_fn(f"   • Palabras clave activas  : {keywords_str}")
            print_fn("─" * 68)
            print_fn("  [1] 📋 Ver TODO el Buzón sin filtros (igual que Webmail UGR) [Por defecto]")
            print_fn("  [2] ●  Ver solo correos NO LEÍDOS")
            print_fn("  [3] 🎓 Ver solo Académicos / Profesores UGR y PRADO (oculta spam/listas)")
            print_fn("  [4] 🎯 Ver solo Mis Filtros Manuales (Profesores / Palabras clave)")
            print_fn("  [5] ➕ Añadir correo o dominio de Profesor (ej. manjavacas@ugr.es, @decsai.ugr.es)")
            print_fn("  [6] 🏷️  Añadir palabra clave de asignatura/asunto (ej. Examen, Nota, Práctica, ED)")
            print_fn("  [7] 🗑️  Limpiar todos los filtros manuales")
            print_fn("  [0] ↩️  Volver al buzón")
            choice = input_fn("\nElige una opción [1-7, 0 para volver]: ").strip()

        if choice == "1":
            return "all"
        if choice == "2":
            return "unread"
        if choice == "3":
            return "academic"
        if choice == "4":
            if not cfg.mail.filter_senders and not cfg.mail.filter_keywords:
                if is_en:
                    print_fn("  ⚠ You haven't added any custom senders or keywords yet. Add one with [5] or [6] first!")
                else:
                    print_fn("  ⚠ Aún no has añadido ningún profesor ni palabra clave. ¡Usa [5] o [6] primero!")
                continue
            return "custom"
        if choice == "5":
            prompt = (
                "  Enter professor email(s) or domain separated by commas: "
                if is_en
                else "  Escribe el correo(s) del profesor o dominio separados por comas: "
            )
            raw = input_fn(prompt).strip()
            if raw:
                for item in raw.split(","):
                    clean = item.strip().lower()
                    if clean and clean not in cfg.mail.filter_senders:
                        cfg.mail.filter_senders.append(clean)
                save_config(cfg)
                print_fn("  ✓ Saved!" if is_en else "  ✓ ¡Filtro de remitente guardado!")
        elif choice == "6":
            prompt = (
                "  Enter subject/course keyword(s) separated by commas: "
                if is_en
                else "  Escribe la palabra(s) clave o siglas separadas por comas: "
            )
            raw = input_fn(prompt).strip()
            if raw:
                for item in raw.split(","):
                    clean = item.strip()
                    if clean and clean not in cfg.mail.filter_keywords:
                        cfg.mail.filter_keywords.append(clean)
                save_config(cfg)
                print_fn("  ✓ Saved!" if is_en else "  ✓ ¡Palabras clave guardadas!")
        elif choice == "7":
            cfg.mail.filter_senders.clear()
            cfg.mail.filter_keywords.clear()
            save_config(cfg)
            if current_view_mode == "custom":
                current_view_mode = "all"
            print_fn("  ✓ Manual filters cleared." if is_en else "  ✓ Filtros manuales eliminados.")
        elif choice in ("0", ""):
            return current_view_mode


def configure_forwarding_interactive(
    cfg: PradoConfig,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> PradoConfig:
    """
    Interactive wizard (`[R]` in TUI or during onboarding) to configure automatic forwarding
    of matching UGR emails to a personal email address.
    """
    is_en = cfg.language == "en"
    print_fn("\n" + "═" * 68)
    if is_en:
        print_fn("↪️  UGR MAIL AUTO-FORWARDING SETUP")
        print_fn("═" * 68)
        status_lbl = "ACTIVE" if (cfg.mail.forward_enabled and cfg.mail.forward_to) else "DISABLED"
        print_fn(f"   • Current Status      : {status_lbl}")
        print_fn(f"   • Destination Email   : {cfg.mail.forward_to or '(not set)'}")
        print_fn(f"   • Forwarding Rule     : {cfg.mail.forward_mode}")
        print_fn(f"   • Professor Filters   : {', '.join(cfg.mail.filter_senders) or '(none)'}")
        print_fn(f"   • Keyword Filters     : {', '.join(cfg.mail.filter_keywords) or '(none)'}")
        print_fn("─" * 68)
        dest_prompt = (
            f"1. Personal email to forward messages to (or 'off' to disable) [{cfg.mail.forward_to or ''}]: "
        )
    else:
        print_fn("↪️  CONFIGURACIÓN DE REENVÍO AUTOMÁTICO DE CORREO UGR")
        print_fn("═" * 68)
        status_lbl = "ACTIVO" if (cfg.mail.forward_enabled and cfg.mail.forward_to) else "DESACTIVADO"
        print_fn(f"   • Estado actual       : {status_lbl}")
        print_fn(f"   • Correo de destino   : {cfg.mail.forward_to or '(no configurado)'}")
        print_fn(f"   • Regla de reenvío    : {cfg.mail.forward_mode}")
        print_fn(f"   • Filtro profesores   : {', '.join(cfg.mail.filter_senders) or '(ninguno)'}")
        print_fn(f"   • Filtro palabras     : {', '.join(cfg.mail.filter_keywords) or '(ninguna)'}")
        print_fn("─" * 68)
        dest_prompt = (
            f"1. Correo personal donde recibir los correos reenviados (o 'off' para desactivar) [{cfg.mail.forward_to or ''}]: "
        )

    entered_dest = input_fn(dest_prompt).strip()
    if entered_dest.lower() in ("off", "no", "none", "desactivar", "0"):
        cfg.mail.forward_enabled = False
        save_config(cfg)
        print_fn(
            "  ✓ Auto-forwarding disabled."
            if is_en
            else "  ✓ Reenvío automático desactivado."
        )
        return cfg

    resolved_dest = entered_dest or (cfg.mail.forward_to or "")
    if not resolved_dest or "@" not in resolved_dest:
        print_fn(
            "  ⚠ No valid destination email provided. Auto-forwarding remains disabled."
            if is_en
            else "  ⚠ No se indicó un correo válido. El reenvío automático sigue desactivado."
        )
        return cfg

    cfg.mail.forward_to = resolved_dest
    cfg.mail.forward_enabled = True

    if is_en:
        print_fn("\n2. Which emails should be forwarded to your personal address?")
        print_fn("   [1] 🎯 Only emails from specific professors or keywords (Custom Filter) [Recommended]")
        print_fn("   [2] 🎓 All Academic / UGR Professor & PRADO emails (excludes Rectorado/newsletter spam)")
        print_fn("   [3] 📋 Every incoming email in my UGR inbox")
        mode_ans = input_fn("   Select rule [1/2/3] [1]: ").strip()
    else:
        print_fn("\n2. ¿Qué correos deseas reenviar automáticamente a tu cuenta personal?")
        print_fn("   [1] 🎯 Solo correos de ciertos profesores o con palabras clave (Filtro Personalizado) [Recomendado]")
        print_fn("   [2] 🎓 Todos los correos académicos de profesores UGR y PRADO (excluye spam/listas del Rectorado)")
        print_fn("   [3] 📋 Todos los correos que entren al buzón UGR")
        mode_ans = input_fn("   Elige regla [1/2/3] [1]: ").strip()

    if mode_ans == "2":
        cfg.mail.forward_mode = "academic"
    elif mode_ans == "3":
        cfg.mail.forward_mode = "all"
    else:
        cfg.mail.forward_mode = "custom"
        current_senders = ", ".join(cfg.mail.filter_senders)
        if is_en:
            s_prompt = (
                f"\n3. Professor emails or domains to forward (comma-separated, e.g. manjavacas@ugr.es, @decsai.ugr.es) [{current_senders}]: "
            )
        else:
            s_prompt = (
                f"\n3. Correos o dominios de profesores a reenviar (separados por comas, ej. manjavacas@ugr.es, @decsai.ugr.es) [{current_senders}]: "
            )
        s_in = input_fn(s_prompt).strip()
        if s_in:
            cfg.mail.filter_senders = [x.strip().lower() for x in s_in.split(",") if x.strip()]

        current_kw = ", ".join(cfg.mail.filter_keywords)
        if is_en:
            k_prompt = (
                f"4. Subject/Course keywords to forward (comma-separated, e.g. Examen, Nota, Práctica, ED) [{current_kw}]: "
            )
        else:
            k_prompt = (
                f"4. Palabras clave en el asunto a reenviar (separadas por comas, ej. Examen, Nota, Práctica, ED) [{current_kw}]: "
            )
        k_in = input_fn(k_prompt).strip()
        if k_in:
            cfg.mail.filter_keywords = [x.strip() for x in k_in.split(",") if x.strip()]

        if not cfg.mail.filter_senders and not cfg.mail.filter_keywords:
            if is_en:
                print_fn("   (No specific filters entered -> defaulting rule to 'academic' so professor emails aren't missed).")
            else:
                print_fn("   (No indicaste filtros específicos -> usando modo 'academic' por defecto para no perder avisos de profesores).")
            cfg.mail.forward_mode = "academic"

    save_config(cfg)
    if is_en:
        print_fn(f"\n✓ Auto-forwarding ACTIVE -> {cfg.mail.forward_to} (mode: {cfg.mail.forward_mode})")
        print_fn("  💡 Original emails remain UNREAD on your UGR server until you open them directly.")
    else:
        print_fn(f"\n✓ ¡Reenvío automático ACTIVO hacia {cfg.mail.forward_to} (modo: {cfg.mail.forward_mode})!")
        print_fn("  💡 Los correos originales se mantienen como NO LEÍDOS en el servidor UGR hasta que los abras tú.")
    return cfg


def _render_inbox_screen(
    messages: List[MailMessage],
    cfg: PradoConfig,
    view_mode: str,
    print_fn: Callable[[str], None] = print,
) -> None:
    is_en = cfg.language == "en"
    mode_labels_es = {
        "all": "TODO EL BUZÓN (Sin filtros — Vista Webmail)",
        "unread": "SOLO NO LEÍDOS",
        "academic": "SOLO ACADÉMICOS / PROFESORES UGR",
        "custom": "MIS FILTROS MANUALES (Profesores / Palabras clave)",
    }
    mode_labels_en = {
        "all": "ALL INBOX (Unfiltered — Webmail View)",
        "unread": "UNREAD ONLY",
        "academic": "ACADEMIC / UGR PROFESSORS ONLY",
        "custom": "MY CUSTOM FILTERS (Professors / Keywords)",
    }
    mode_label = (mode_labels_en if is_en else mode_labels_es).get(view_mode, view_mode.upper())
    fwd_status = (
        f"ON ➔ {cfg.mail.forward_to} ({cfg.mail.forward_mode})"
        if (cfg.mail.forward_enabled and cfg.mail.forward_to)
        else "OFF"
    )

    print_fn("\n╔══════════════════════════════════════════════════════════════════════════════╗")
    if is_en:
        print_fn("║  📬 PradoOS — UGR Institutional Mail Reader (@correo.ugr.es)                 ║")
    else:
        print_fn("║  📬 PradoOS — Lector de Correo Institucional UGR (@correo.ugr.es)            ║")
    print_fn("╠══════════════════════════════════════════════════════════════════════════════╣")
    if is_en:
        print_fn(f"║  🔍 View Filter : {mode_label:<58} ║")
        print_fn(f"║  ↪️  Auto-Forward: {fwd_status:<58} ║")
        print_fn("╠══════════════════════════════════════════════════════════════════════════════╣")
        print_fn("║  QUICK ACTIONS:  [F] 🔍 Set Filters / View   [R] ↪️ Auto-Forwarding Rules    ║")
        print_fn("║                  [S] 🔄 Refresh Inbox        [1..N] 📖 Open & Read Email     ║")
    else:
        print_fn(f"║  🔍 Vista actual: {mode_label:<58} ║")
        print_fn(f"║  ↪️  Auto-Reenvío: {fwd_status:<58} ║")
        print_fn("╠══════════════════════════════════════════════════════════════════════════════╣")
        print_fn("║  OPCIONES RÁPIDAS: [F] 🔍 Filtros Manuales   [R] ↪️ Reglas de Reenvío        ║")
        print_fn("║                    [S] 🔄 Actualizar Buzón   [1..N] 📖 Abrir y Leer Correo   ║")
    print_fn("╚══════════════════════════════════════════════════════════════════════════════╝")

    if not messages:
        if is_en:
            print_fn("\n  (No emails match the current view filter.)")
        else:
            print_fn("\n  (No hay correos que coincidan con el filtro de vista actual.)")
        return

    if is_en:
        print_fn(f"\n  {'#':>3}  {'St':<3} {'Date':<16} {'From':<26} {'Subject'}")
    else:
        print_fn(f"\n  {'#':>3}  {'Est':<3} {'Fecha':<16} {'De (Remitente)':<26} {'Asunto'}")
    print_fn("  " + "─" * 76)

    for idx, m in enumerate(messages, start=1):
        unread_mark = "●" if m.is_unread else " "
        acad_mark = "🎓" if m.is_academic else "  "
        att_mark = "📎" if m.attachments else ""
        sender_short = (m.sender[:24] + "…") if len(m.sender) > 25 else m.sender
        subj_short = (m.subject[:38] + "…") if len(m.subject) > 39 else m.subject
        print_fn(
            f"  [{idx:>2}] {unread_mark}{acad_mark} {m.date_str:<16} {sender_short:<26} {subj_short} {att_mark}"
        )


def _read_single_email_Loop(
    msg_summary: MailMessage,
    client: UgrMailClient,
    cfg: PradoConfig,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    folder_picker_fn: Callable[[str], Optional[Path]] = prompt_folder_picker_gui,
) -> None:
    """
    Opens a single email in full, marks it as Read (`\\Seen`) on the UGR server,
    and allows saving attachments via the native OS graphical folder picker.
    """
    is_en = cfg.language == "en"
    try:
        full_msg = client.read_message(msg_summary.uid, mark_seen=True)
        msg_summary.is_unread = False
    except Exception:
        full_msg = msg_summary
        msg_summary.is_unread = False

    print_fn("\n" + "═" * 78)
    print_fn(f"📧 {full_msg.subject}")
    print_fn("─" * 78)
    print_fn(f"• {'From' if is_en else 'De'}     : {full_msg.sender}")
    print_fn(f"• {'Date' if is_en else 'Fecha'}  : {full_msg.date_str}")
    if full_msg.attachments:
        att_list = ", ".join(f"[{a.index}] {a.filename} ({_format_size(a.size_bytes)})" for a in full_msg.attachments)
        print_fn(f"• {'Attachments' if is_en else 'Adjuntos'} 📎 : {att_list}")
    print_fn("═" * 78)
    print_fn(full_msg.body_text or ("(Empty message body)" if is_en else "(Mensaje sin contenido de texto)"))
    print_fn("═" * 78)

    while True:
        if full_msg.attachments:
            prompt = (
                "\nOptions: [A] 📎 Save Attachment(s) (opens GUI folder window) | [F] ↪️ Forward this email | [Enter/0] Back: "
                if is_en
                else "\nOpciones: [A] 📎 Guardar Adjunto(s) (abre ventana gráfica de carpetas) | [F] ↪️ Reenviar este correo | [Enter/0] Volver: "
            )
        else:
            prompt = (
                "\nOptions: [F] ↪️ Forward this email | [Enter/0] Back to Inbox: "
                if is_en
                else "\nOpciones: [F] ↪️ Reenviar este correo | [Enter/0] Volver al buzón: "
            )

        act = input_fn(prompt).strip().lower()
        if act in ("", "0", "q", "volver", "back"):
            break

        if act == "a" and full_msg.attachments:
            selected_atts = full_msg.attachments
            if len(full_msg.attachments) > 1:
                idx_prompt = (
                    f"  Which attachment [1-{len(full_msg.attachments)}, or 'all' for all] [all]: "
                    if is_en
                    else f"  ¿Qué adjunto deseas guardar [1-{len(full_msg.attachments)}, o 'all' para todos] [all]: "
                )
                which = input_fn(idx_prompt).strip().lower()
                if which.isdigit():
                    num = int(which)
                    selected_atts = [a for a in full_msg.attachments if a.index == num] or full_msg.attachments

            for att in selected_atts:
                gui_title = (
                    f"Select folder to save '{att.filename}'"
                    if is_en
                    else f"Selecciona la carpeta donde guardar '{att.filename}'"
                )
                print_fn(
                    f"  🗂️  Opening graphical folder selector for '{att.filename}'..."
                    if is_en
                    else f"  🗂️  Abriendo ventana gráfica para elegir dónde guardar '{att.filename}'..."
                )
                picked_dir = folder_picker_fn(gui_title)
                if picked_dir is None:
                    fallback_prompt = (
                        f"  Destination folder path [{cfg.courses_root}]: "
                        if is_en
                        else f"  Ruta de carpeta de destino [{cfg.courses_root}]: "
                    )
                    manual_dir = input_fn(fallback_prompt).strip()
                    picked_dir = Path(manual_dir).expanduser() if manual_dir else cfg.courses_root

                saved_path = save_attachment_to_folder(att, picked_dir)
                print_fn(
                    f"  ✓ Saved attachment to: {saved_path}"
                    if is_en
                    else f"  ✓ Adjunto guardado en: {saved_path}"
                )

        elif act == "f":
            default_to = cfg.mail.forward_to or ""
            to_prompt = (
                f"  Forward to email [{default_to}]: "
                if is_en
                else f"  Reenviar al correo [{default_to}]: "
            )
            target_to = input_fn(to_prompt).strip() or default_to
            if target_to and "@" in target_to:
                try:
                    client.forward_message(full_msg, target_to)
                    print_fn(
                        f"  ✓ Email forwarded to {target_to}!"
                        if is_en
                        else f"  ✓ ¡Correo reenviado con éxito a {target_to}!"
                    )
                except Exception as exc:
                    print_fn(f"  ✗ Error: {exc}")


def run_mail_tui(
    client: Optional[UgrMailClient] = None,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    folder_picker_fn: Callable[[str], Optional[Path]] = prompt_folder_picker_gui,
) -> int:
    """
    Main interactive TUI loop for `prado mail`.
    Starts with `view_mode = "all"` (full unfiltered inbox like Webmail),
    while exposing `[F]` Filters and `[R]` Auto-Forwarding right at the top.
    """
    cfg = load_config()
    mail_client = client or UgrMailClient(config=cfg)
    is_en = cfg.language == "en"

    print_fn(
        "\n🔄 Connecting to UGR Mail (correo.ugr.es)..."
        if is_en
        else "\n🔄 Conectando con el Correo Institucional UGR (correo.ugr.es)..."
    )
    try:
        sync_res = mail_client.sync_and_forward()
        all_messages = [MailMessage.from_dict(m) for m in sync_res.get("messages", [])]
        if sync_res.get("forwarded", 0) > 0:
            print_fn(
                f"  ↪️ Auto-forwarded {sync_res['forwarded']} new matching email(s) to {cfg.mail.forward_to}."
                if is_en
                else f"  ↪️ Se han reenviado automáticamente {sync_res['forwarded']} correo(s) nuevo(s) a {cfg.mail.forward_to}."
            )
    except Exception as exc:
        # Fallback to cached messages if offline
        cache = load_mail_cache()
        cached_raw = cache.get("messages", [])
        if cached_raw:
            print_fn(f"  ⚠ Offline / Connection warning ({exc}). Showing cached inbox.")
            all_messages = [MailMessage.from_dict(m) for m in cached_raw]
        else:
            print_fn(f"  ✗ Could not connect to UGR Mail: {exc}")
            return 1

    # Always open with the full unfiltered inbox ('all'), just like UGR Webmail
    view_mode = "all"

    while True:
        cfg = load_config()
        mail_client.config = cfg
        visible_messages = [
            m
            for m in all_messages
            if matches_mail_filter(
                m,
                mode=view_mode,
                filter_senders=cfg.mail.filter_senders,
                filter_keywords=cfg.mail.filter_keywords,
            )
        ]

        _render_inbox_screen(visible_messages, cfg=cfg, view_mode=view_mode, print_fn=print_fn)

        prompt = (
            "\nAction [1..N = Read email, F = Filters/View, R = Auto-Forwarding, S = Refresh, 0 = Exit]: "
            if is_en
            else "\nAcción [1..N = Leer correo, F = Filtros/Vista, R = Auto-Reenvío, S = Actualizar, 0 = Salir]: "
        )
        try:
            ans = input_fn(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print_fn("")
            return 0

        low = ans.lower()
        if low in ("0", "q", "exit", "salir"):
            return 0

        if low == "f":
            view_mode = configure_mail_filters_interactive(
                cfg=cfg,
                current_view_mode=view_mode,
                input_fn=input_fn,
                print_fn=print_fn,
            )
            continue

        if low == "r":
            cfg = configure_forwarding_interactive(cfg=cfg, input_fn=input_fn, print_fn=print_fn)
            continue

        if low == "s":
            print_fn(
                "🔄 Refreshing UGR inbox..."
                if is_en
                else "🔄 Actualizando buzón UGR y comprobando reglas de reenvío..."
            )
            try:
                sync_res = mail_client.sync_and_forward()
                all_messages = [MailMessage.from_dict(m) for m in sync_res.get("messages", [])]
            except Exception as exc:
                print_fn(f"  ✗ Error: {exc}")
            continue

        if ans.isdigit():
            idx = int(ans)
            if 1 <= idx <= len(visible_messages):
                target_msg = visible_messages[idx - 1]
                _read_single_email_Loop(
                    msg_summary=target_msg,
                    client=mail_client,
                    cfg=cfg,
                    input_fn=input_fn,
                    print_fn=print_fn,
                    folder_picker_fn=folder_picker_fn,
                )
            else:
                print_fn(
                    f"  ⚠ Invalid number (choose between 1 and {len(visible_messages)})."
                    if is_en
                    else f"  ⚠ Número no válido (elige entre 1 y {len(visible_messages)})."
                )
        else:
            print_fn(
                "  ⚠ Unknown option. Use a number [1..N], F, R, S, or 0."
                if is_en
                else "  ⚠ Opción no reconocida. Usa un número [1..N], F, R, S o 0."
            )
