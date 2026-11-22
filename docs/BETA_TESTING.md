# 🧪 PradoOS Desktop — Closed Beta Guide (UGR & Erasmus)

> ⚠️ **Closed Beta Notice:** PradoOS is currently undergoing an informal technical review with **OSL UGR** and **CEPRUD**. Please use this build only for personal testing and **do not redistribute the `.zip` or share it in public university groups yet**.

---

## 1. Install & First Launch (No Terminal Required)

### 🪟 Windows 10 / 11 (`PradoOS-windows.zip`)
1. **Unzip completely first** (Right-click `PradoOS-windows.zip` → **Extract All…**). Do **not** run `PradoOS.exe` directly from inside the preview `.zip` folder.
2. Open the extracted `PradoOS` folder and double-click **`PradoOS.exe`**.
3. If **Microsoft SmartScreen** ("Windows protected your PC") appears on first launch (expected while student beta builds are unsigned):
   - Click **More info** (*Más información*) → **Run anyway** (*Ejecutar de todas formas*).
4. PradoOS will appear in your **System Tray** (near the clock / under the `^` arrow) and open the **Setup Card**.

### 🍎 macOS (`PradoOS-macos.zip`)
1. Download and unzip **`PradoOS-macos.zip`** (drag `PradoOS.app` to `Applications` if you like).
2. On first launch, **Right-click (or Ctrl-click) `PradoOS.app` → Open** → **Open** once to approve the unsigned student beta build.
3. PradoOS will live in your top **Menu Bar** (graduation cap icon) and open the **Setup Card**.

---

## 2. 30-Second Initial Setup

1. Pick your language (`ES` / `EN` / `IT` / `FR`) in the top-right corner of the Setup Card.
2. Choose your PRADO portal (`PradoGrado` or `PradoPosgrado`).
3. Enter your **`@correo.ugr.es`** email and UGR *Acceso Identificado* password (stored 100% locally in Windows Credential Manager / encrypted vault — never sent to third-party servers).
4. Choose where to save your courses folder using **Choose…** (*Elegir…*) and pick **Mirror** (exact PRADO layout) or **Smart** (`Teoría/` & `Prácticas/`).
5. Click **Connect & Sync**. Enter the **6-digit 2FA code** sent to your `@correo.ugr.es` inbox (valid for 30 days on your device).
6. *(Optional)* Open the **Mail & Options** tab to enable **Auto-Sync**, **Desktop Notifications**, **Launch at Login**, or selective forwarding from `@correo.ugr.es` to your personal Gmail/Outlook.

---

## 3. How to Send Useful Feedback

Please reply via WhatsApp/Telegram or open a [Beta Feedback Issue](https://github.com/LorSt4r/prado-os/issues/new?template=beta_feedback.md) with:
1. **Your OS & Faculty** (e.g., Windows 11, Economics / ETSIIT / Erasmus).
2. **Any blocker on launch** (screenshot of SmartScreen, antivirus, or folder picker).
3. **PRADO completeness check:** Compare your synced folder against PRADO web — did any course, PDF, link, or deadline miss?
4. **Doctor check (if anything fails):** Open Tray → **Preferences & Help → Doctor Diagnostics** and send a screenshot (it contains **zero passwords or personal cookies**).
5. **Day-5 gut check:** What saved you the most time, what annoyed you, and what feature do you want next (e.g., *Calificaciones* grade alerts vs local AI study assistant on your PDFs)?
