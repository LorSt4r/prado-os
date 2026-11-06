# 🎓 PradoOS (`prado-os`) — Documentation en Français

**Le moteur de synchronisation et de flux académique intelligent pour PRADO UGR (`pradogrado`, `pradoposgrado`, `prado.ugr.es`) et Moodle.**  
*Disponible pour macOS, Linux Desktop et Windows.*

[![Release: v0.2.0-beta](https://img.shields.io/badge/release-v0.2.0--beta-orange.svg)](https://github.com/LorSt4r/prado-os/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](../LICENSE)
[![Platform: macOS | Linux | Windows](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-informational)](#)
[![Tests: 727 Passing](https://img.shields.io/badge/tests-727%20passed-brightgreen)](https://github.com/LorSt4r/prado-os/actions)

> 🌐 **Autres langues / Other languages:** [🇪🇸 Español](../README.md#-documentación-en-español) | [🇬🇧 English](../README.md#-english-documentation) | [🇮🇹 Italiano](README.it.md)

---

## 🇫🇷 D'un Besoin Réel à Grenade à un Projet Open-Source

**PradoOS** a été développé par **Lorenzo Vasile**, étudiant en ingénierie informatique à l'*Università degli Studi di Palermo (UniPa)* durant son séjour **Erasmus+** à l'*Universidad de Granada (UGR, ETSIIT)* (Année 2026/2027).  
Face au défi de concilier des cours exigeants de différents départements (Structures de Données, Modèles de Calcul, Vision par Ordinateur, Théorie de l'Information et Systèmes d'Exploitation), est née la volonté d'optimiser le temps d'étude et **d'éliminer définitivement les tâches manuelles répétitives** : télécharger les PDF un par un, surveiller les forums dispersés et suivre des dates limites changeantes.

---

## 💡 Que fait PradoOS pour vous ?

1. 📥 **Vos cours toujours à jour sur votre ordinateur :**  
   Détecte automatiquement toutes vos matières sur PRADO (`pradogrado`, `pradoposgrado`, `ceprud`) et télécharge les diapositives, notes et énoncés de TP dans votre dossier local.
2. 🛡️ **Garantie Zéro-Écrasement :**  
   Si vous modifiez un notebook Jupyter (`.ipynb`), rédigez du code C++/Python ou un rapport et que l'enseignant met à jour un fichier sur PRADO, **votre travail local n'est jamais écrasé**. PradoOS détecte les modifications par hachage SHA-256 et enregistre la version du professeur à côté sous la forme `{fichier}_server_{date}.ext`.
3. 📅 **Échéances et examens directement sur Google Calendar :**  
   Envoie automatiquement vos dates limites sur Google Calendar avec alertes échelonnées (3 jours, 1 jour et 2 heures avant pour les examens ; 2 jours, 1 jour et 3 heures avant pour les TP).
4. 🔑 **Jeton de confiance 30 jours (2FA simplifié) :**  
   Saisissez votre code de double authentification une seule fois par mois. Votre mot de passe est stocké uniquement dans le trousseau sécurisé de votre système d'exploitation (macOS Keychain, Windows Credential Manager ou Linux SecretService), jamais en clair.
5. 📬 **Lecteur de Courriel UGR et Redirection Automatique (`prado mail`) :**  
   Consultez votre boîte `@correo.ugr.es` directement dans le terminal et redirigez automatiquement les avis d'enseignants spécifiques vers votre adresse personnelle (`@gmail.com`, `@icloud.com`, etc.).
6. 📂 **Sélecteur Graphique Natif (Finder / Explorateur de fichiers) :**  
   Pendant la configuration, appuyez sur `G` pour choisir graphiquement votre dossier de destination.

---

## 🚀 Installation Rapide en 1 Clic (Sans prérequis)

> 💡 Aucun besoin d'avoir Python ou Git préinstallés. Le script installe un environnement isolé et lance automatiquement l'assistant de configuration (choisissez **Français**).

**macOS et Linux Desktop :**
```bash
curl -fsSL https://raw.githubusercontent.com/LorSt4r/prado-os/main/install.sh | bash
```

**Windows (PowerShell) :**
```powershell
irm https://raw.githubusercontent.com/LorSt4r/prado-os/main/install.ps1 | iex
```

*(Si vous lancez `prado` sans arguments dans votre terminal, un menu interactif numéroté s'ouvre).*

---

## 🛠️ Commandes Principales

| Commande | Description |
|---|---|
| `prado` | Ouvre le menu interactif principal. |
| `prado onboard` | Lance l'assistant de configuration pas à pas en français. |
| `prado sync --adopt` | Synchronise les nouveaux cours, met à jour `DASHBOARD.md` et vérifie les courriels. |
| `prado mail` | Ouvre le lecteur de courriels `@correo.ugr.es` et les filtres. |
| `prado gcalendar` | Synchronise les échéances avec Google Calendar. |
| `prado doctor` | Diagnostic du réseau UGR, des identifiants et des permissions. |
| `prado daemon install` | Active la synchronisation automatique toutes les 4 heures en arrière-plan. |
| `prado star` | Laissez une étoile sur GitHub si l'outil vous fait gagner du temps ! |

---

## 🤖 Utilisation avec un Assistant IA (Antigravity, Claude Code, Cursor, Codex)

Collez ce message dans votre assistant IA :
```text
Installe et configure https://github.com/LorSt4r/prado-os en suivant BOOTSTRAP.md
```
L'assistant lira [`BOOTSTRAP.md`](../BOOTSTRAP.md), vous répondra en français et terminera la configuration en moins de 60 secondes.

---

## 📜 Licence
Distribué sous licence copyleft **GNU Affero General Public License v3.0 (`AGPL-3.0`)**.  
Créé par **Lorenzo Vasile** pour la communauté étudiante de l'ETSIIT et de l'UGR.
