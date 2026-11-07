# 🎓 PradoOS (`prado-os`) — Documentazione in Italiano

**Il motore di sincronizzazione e flusso accademico intelligente per PRADO UGR (`pradogrado`, `pradoposgrado`, `prado.ugr.es`) e Moodle.**  
*Disponibile per macOS, Linux Desktop e Windows.*

[![Release: v0.2.0-beta](https://img.shields.io/badge/release-v0.2.0--beta-orange.svg)](https://github.com/LorSt4r/prado-os/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](../LICENSE)
[![Platform: macOS | Linux | Windows](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-informational)](#)
[![Tests: 747 Passing](https://img.shields.io/badge/tests-747%20passed-brightgreen)](https://github.com/LorSt4r/prado-os/actions)

> 🌐 **Pagina Web di Download Diretto (1 Clic):** **[https://lorst4r.github.io/prado-os/](https://lorst4r.github.io/prado-os/)**  
> 🌍 **Altre lingue / Other languages:** [🇪🇸 Español](../README.md#-documentación-en-español) | [🇬🇧 English](../README.md#-english-documentation) | [🇫🇷 Français](README.fr.md)

<p align="center">
  <img src="../assets/screens/gui_01_dashboard.png" alt="PradoOS — Configurazione Compatta e Barra dei Menu" width="520">
</p>

---

## 🇮🇹 Da una Necessità Reale a Granada a un Progetto Open-Source

**PradoOS** è stato sviluppato da **Lorenzo Vasile**, studente di Ingegneria Informatica dell'*Università degli Studi di Palermo (UniPa)* durante il suo semestre **Erasmus+** presso l'*Universidad de Granada (UGR, ETSIIT)* (A.A. 2026/2027).  
Dovendo conciliare corsi impegnativi di diversi dipartimenti (Estructura de Datos, Modelos de Computación, Visión por Computador, Teoría de la Información e Sistemas Operativos), è nata l'esigenza di ottimizzare il tempo ed **eliminare del tutto le perdite di tempo manuali**: scaricare PDF uno alla volta, controllare forum dispersi, organizzare cartelle locali e tenere d'occhio scadenze che cambiano continuamente.

---

## 💡 Cosa fa PradoOS per te?

1. 📥 **I tuoi corsi sempre aggiornati sul computer in automatico:**  
   Rileva tutte le materie in cui sei iscritto su PRADO (`pradogrado`, `pradoposgrado`, `ceprud`) e scarica slide, dispense e tracce di laboratorio nella tua cartella locale.
2. 🛡️ **Garanzia Zero-Sovrascritture:**  
   Se risolvi una pratica, modifichi un notebook Jupyter (`.ipynb`) o compili codice C++/Python e il professore carica un aggiornamento su PRADO, **il tuo lavoro locale non viene mai sovrascritto né cancellato**. PradoOS rileva le modifiche tramite hash SHA-256 e salva l'aggiornamento del professore a fianco come `{file}_server_{data}.ext`.
3. 📅 **Scadenze ed esami direttamente su Google Calendar:**  
   Invia le date limite su Google Calendar con notifiche popup a scaglioni (3 giorni, 1 giorno e 2 ore prima per gli esami; 2 giorni, 1 giorno e 3 ore prima per i progetti).
4. 🔑 **Token di fiducia a 30 giorni (MFA comodo):**  
   Inserisci il secondo fattore (2FA) solo una volta al mese. La password è salvata esclusivamente nel Portachiavi cifrato del tuo sistema operativo (macOS Keychain, Windows Credential Manager o Linux SecretService), mai in chiaro.
5. 📬 **Lettore di Posta UGR integrato e Inoltro Automatico (`prado mail`):**  
   Leggi la casella `@correo.ugr.es` direttamente dal terminale e imposta regole per inoltrare automaticamente comunicazioni di professori o materie specifiche al tuo indirizzo personale (`@gmail.com`, `@icloud.com`, ecc.).
6. 📂 **Selettore Grafico Nativo (Finder / Esplora Risorse):**  
   Durante la configurazione puoi premere `G` per scegliere graficamente dove salvare i tuoi file con la finestra nativa del tuo sistema operativo.

---

## 🚀 Installazione Rapida

### 🌟 Opzione 1: App Grafica Desktop — Centro di Controllo + Barra dei Menu (Zero Terminale)
Non serve aprire il terminale né installare Python o Git!
Scarica l'applicazione pre-compilata direttamente da **[GitHub Releases](https://github.com/LorSt4r/prado-os/releases)**:
- 🍏 **macOS:** Scarica [`PradoOS-macos.zip`](https://github.com/LorSt4r/prado-os/releases), estrai e apri `PradoOS.app` (apre la finestra nativa del **Centro di Controllo PradoOS** e resta attiva nella **Barra dei Menu superiore**).
- 🪟 **Windows:** Scarica [`PradoOS-windows.zip`](https://github.com/LorSt4r/prado-os/releases), estrai ed esegui `PradoOS.exe` (apre il **Centro di Controllo PradoOS** e resta nella **System Tray** accanto all'orologio).

**Cosa include il Centro di Controllo Desktop:**
- 🪄 **Wizard di Primo Avvio e Modale 2FA Live:** Scelta lingua (`IT`, `ES`, `EN`, `FR`), portale PRADO, salvataggio credenziali nel Portachiavi nativo, inserimento codice MFA a 6 cifre in tempo reale e selettore grafico della cartella.
- 📊 **Dashboard in Tempo Reale:** Barra di avanzamento materia per materia, log live, file protetti da sovrascrittura (SHA-256), scadenze ed esami imminenti e apertura rapida in Finder/Explorer.
- 📚 **Gestione Materie e Sottogruppi:** Attiva/disattiva corsi, imposta i sottogruppi di laboratorio (`C2`, `A3`, `B1`) e scegli tra modalità `mirror` o `smart`.
- 📬 **Lettore Grafico Posta UGR (`@correo.ugr.es`) & Auto-Inoltro:** Visualizzazione split-pane che preserva lo stato di non letto (`BODY.PEEK[]`), download allegati con selettore cartella nativo e inoltro selettivo automatico verso `@gmail.com` / `@icloud.com`.
- 📅 **Calendario, Daemon 4h & Diagnostica Doctor:** Sincronizzazione con 1 clic su Google Calendar / Apple Calendar (`deadlines.ics`), attivazione sync automatica ogni 4 ore e verifica delle 9 sonde diagnostiche (`Doctor`).

*(Se hai già installato la CLI tramite pip/uv, puoi avviare il Centro di Controllo e la tray in qualsiasi momento con `prado app` o `prado-app`).*

### Opzione 2: Installazione Rapida via Terminale (Senza prerequisiti)

> 💡 Non serve avere Python né Git già installati. L'installer scarica un ambiente isolato nello spazio utente e lancia automaticamente l'assistente iniziale (dove puoi scegliere **Italiano**).

**macOS e Linux Desktop:**
```bash
curl -fsSL https://raw.githubusercontent.com/LorSt4r/prado-os/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/LorSt4r/prado-os/main/install.ps1 | iex
```

*(Se esegui `prado` nel terminale senza argomenti, si apre il menu interattivo numerato).*

---

## 🛠️ Comandi Principali

| Comando | Descrizione |
|---|---|
| `prado` | Apre il menu interattivo principale. |
| `prado app / prado gui` | Avvia l'applicazione nativa nella barra dei menu (macOS) o tray (Windows/Linux). |
| `prado onboard` | Esegue il wizard guidato di configurazione in italiano. |
| `prado sync --adopt` | Scarica i nuovi materiali, aggiorna `DASHBOARD.md` e controlla la posta. |
| `prado mail` | Apre il lettore di posta `@correo.ugr.es` con filtri e regole di inoltro. |
| `prado gcalendar` | Sincronizza le scadenze con Google Calendar. |
| `prado doctor` | Diagnostica di rete UGR, credenziali e permessi. |
| `prado daemon install` | Attiva la sincronizzazione automatica ogni 4 ore in background. |
| `prado star` | Lascia una stella al progetto su GitHub se ti fa risparmiare tempo! |

---

## 🤖 Uso con Assistenti IA (Antigravity, Claude Code, Cursor, Codex)

Basta incollare questo messaggio nel tuo assistente IA:
```text
Installa e configura https://github.com/LorSt4r/prado-os seguendo BOOTSTRAP.md
```
L'agente leggerà [`BOOTSTRAP.md`](../BOOTSTRAP.md), ti parlerà in italiano e completerà la configurazione iniziale in meno di 60 secondi.

---

## 📜 Licenza
Rilasciato sotto licenza copyleft **GNU Affero General Public License v3.0 (`AGPL-3.0`)**.  
Creato da **Lorenzo Vasile** per la comunità universitaria dell'ETSIIT e dell'UGR.
