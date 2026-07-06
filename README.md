# 🤖 AntigraCall — Telegram Bot per Google Antigravity CLI

**AntigraCall** è un'interfaccia bot Telegram privata per interagire in mobilità con la potenza di **Google Antigravity CLI (`agy`)** configurata sul tuo PC di casa o ufficio. Consente di scrivere ed eseguire codice, gestire progetti (es. compilation LaTeX o creazione progetti Android) ed effettuare modifiche direttamente dal telefono, mantenendo contesti separati e sincronizzazione dei file bidirezionale.

---

## ✨ Funzionalità Chiave

* 🧠 **Integrazione Nativa con agy**: Interazione asincrona non-interattiva sicura, eredita le chiavi e la quota del tuo PC locale.
* 🗂️ **Gestione Workspace Avanzata**: Comando `/workspace` con tastiera inline a due livelli (Categoria → Sottocartella) per navigare tra i tuoi progetti (Progetti Personali e Università).
* 💾 **Persistenza & Sessioni Multi-Turn**: Database SQLite (`db/antigracall.db`) locale che memorizza lo storico dei messaggi e permette di ripristinare contesti conversazionali storici tramite il comando `/history` ed il comando `/new`.
* 🔔 **Notifiche Proattive & Interruzione**:
  - Se un'operazione dura più di 15 secondi, compare una barra di caricamento testuale dinamica ed il pulsante inline `🛑 Interrompi` per terminare istantaneamente il subprocess `agy`.
  - Comando `/stop` per fermare i task in corso.
* 📥 **Sincronizzazione File Bidirezionale**:
  - **Upload (Telegram → PC)**: Trascina foto o documenti in chat per scaricarli direttamente nel workspace attivo ed inviarli in pasto all'agente per l'elaborazione.
  - **Download (PC → Telegram)**: Il bot rileva qualsiasi file creato o modificato dall'agente (es. grafici `.png`, tabelle `.xlsx`, o file `.py` modificati) e te lo rispedisce automaticamente in chat.
  - **Download Diretto**: Usa `/get <percorso_relativo>` per scaricare esplicitamente qualsiasi file dal tuo workspace.
* 📊 **Pannello Admin (`/status`)**: Cruscotto con uptime del bot, directory attiva, ID sessione e stato dell'agente (`idle` o `in esecuzione`).
* 🚀 **Avvio Automatico Silenzioso**: Configurazione dell'autostart su Windows per girare invisibilmente in background all'avvio del PC tramite `pythonw.exe`.

---

## 🛠️ Requisiti & Installazione

### Requisiti
- Windows OS con Python 3.11+
- [Antigravity CLI](https://antigravity.google) installata ed autenticata sul PC (`agy` deve rispondere correttamente a `agy -p "ciao"`).

### Setup
1. **Clona la cartella** o posizionati nella directory di installazione.
2. **Installa le dipendenze** nel tuo ambiente virtuale:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate.ps1
   pip install -e .
   ```
3. **Crea e configura il file `.env`**:
   Copia il file `.env.example` in `.env` e imposta:
   - `TELEGRAM_BOT_TOKEN`: Il token segreto fornito da [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_ALLOWED_USER_ID`: Il tuo ID Telegram numerico (solo tu potrai interagire col bot).

4. **Configura le cartelle di lavoro (`workspaces.yaml`)**:
   Copia il file `config/workspaces.yaml.example` in `config/workspaces.yaml` e modifica le sezioni `workspaces` per specificare i percorsi delle cartelle che desideri rendere disponibili al bot. Adatta i nomi delle categorie e delle sottocartelle alle tue esigenze.
   
5. **Configura le impostazioni del bot (`settings.yaml`)**:
   Copia il file `config/settings.yaml.example` in `config/settings.yaml` e modifica le impostazioni del bot secondo le tue preferenze:
   - `agent_timeout`: Tempo massimo in secondi per le risposte dell'agente.
   - `max_message_length`: Lunghezza massima dei messaggi inviati su Telegram.
   - `code_file_threshold`: Soglia di caratteri oltre la quale il codice viene salvato come file.

---

## 🚀 Avvio del Bot

### Avvio Manuale (per test e debug)
Esegui da PowerShell:
```powershell
.\.venv\Scripts\python.exe -m antigracall.main
```

### Configurazione Avvio Automatico all'avvio di Windows (Silenzioso)
Abbiamo fornito uno script PowerShell automatizzato che crea un collegamento nella cartella `Esecuzione automatica` di Windows per avviare il bot in background (senza finestre del terminale visibili) usando `pythonw.exe`:

1. Apri **PowerShell** e posizionati nella cartella `scripts`:
   ```powershell
   cd "Percorso\Alla\Cartella\AntigraCall\scripts"
   ```
2. Esegui lo script:
   ```powershell
   .\install_autostart.ps1
   ```
Al prossimo riavvio di Windows, il bot sarà operativo in background!

---

## 🤖 Guida ai Comandi Telegram

| Comando | Descrizione |
|:---|:---|
| `/start` | Avvia il bot e mostra il messaggio di benvenuto. |
| `/workspace` | Mostra la tastiera inline dinamica a due livelli per impostare la cartella di lavoro corrente. |
| `/workspace current` | Mostra il percorso del workspace attualmente attivo. |
| `/new` | Chiude la conversazione corrente ed avvia una sessione pulita (genera un nuovo UUID per `agy`). |
| `/clear` | Cancella permanentemente la sessione corrente dal database locale e resetta la memoria. |
| `/history` | Mostra l'elenco delle ultime 10 sessioni aperte con anteprima del primo messaggio, consentendoti di scambiarle al volo. |
| `/status` | Visualizza l'uptime del bot, la cartella attiva, l'ID sessione corrente e se l'agente sta elaborando o è in attesa. |
| `/stop` | Forza l'uccisione immediata del task `agy` in esecuzione sul PC. |
| `/get <percorso>` | Scarica un file specifico dal workspace (es: `/get src/main.py`). |

---

## 📂 Struttura del Progetto

```
AntigraCall/
│
├── config/
│   ├── settings.yaml      # Impostazioni generali (limiti, timeout, skill native)
│   └── workspaces.yaml    # Configurazione ad albero delle cartelle di lavoro
│
├── db/
│   └── antigracall.db     # Database SQLite (creato automaticamente all'avvio)
│
├── logs/
│   └── antigracall.log    # File dei log con rotazione automatica
│
├── scripts/
│   ├── install_autostart.ps1  # Script PowerShell per l'installazione in Startup
│   └── run_background.vbs    # Script VBS per eseguire il bot in background invisibile
│
├── src/antigracall/
│   ├── main.py            # Entry point dell'applicazione (polling loop con retry)
│   ├── agent/
│   │   ├── manager.py     # Interfaccia con agy.exe e rilevamento file modificati
│   │   └── formatter.py   # Parser Markdown-to-HTML sicuro per Telegram
│   ├── bot/
│   │   ├── handlers/      # Router e gestione dei comandi start, chat, admin, session, workspace
│   │   ├── keyboards/     # Generazione tastiere inline per cronologia e cartelle
│   │   └── middlewares/   # Middleware di autorizzazione utente (sicurezza)
│   └── utils/
│       ├── config.py      # Caricamento delle configurazioni YAML e .env
│       └── logger.py      # Inizializzazione logging
│
└── pyproject.toml         # Gestione delle dipendenze di progetto
```
