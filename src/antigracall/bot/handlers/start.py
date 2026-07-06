from aiogram import Router, types
from aiogram.filters import Command, CommandStart

router = Router(name="start")

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Gestisce il comando /start."""
    welcome_text = (
        "🚀 <b>Benvenuto in AntigraCall!</b>\n\n"
        "Questo bot ti permette di controllare l'agente di sviluppo <b>Antigravity</b> "
        "direttamente sul tuo PC da remoto.\n\n"
        "<b>Comandi disponibili:</b>\n"
        "📁 /workspace - Seleziona o mostra il workspace attivo\n"
        "🧠 /model - Seleziona il modello dell'agente attivo\n"
        "💬 /new - Inizia una nuova sessione conversazionale pulita\n"
        "🗄️ /history - Mostra le sessioni storiche con preview per ripristinarle\n"
        "🧹 /clear - Cancella permanentemente la sessione corrente dal DB\n"
        "📊 /status - Mostra lo stato del sistema, uptime e dell'agente\n"
        "🛑 /stop - Interrompe l'elaborazione dell'agente in corso\n"
        "📝 /plan - Scarica l'ultimo implementation plan della sessione\n"
        "📥 /get &lt;percorso&gt; - Scarica un file dal workspace (es. <code>/get src/main.py</code>)\n"
        "❓ /help - Mostra questa guida\n\n"
        "Scrivi un messaggio di testo normale per inviarlo all'agente nella sessione attiva, "
        "oppure trascina un file/immagine in chat per salvarlo nella cartella <code>telegram_uploads</code>."
    )
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Gestisce il comando /help."""
    help_text = (
        "💡 <b>Guida ai Comandi di AntigraCall:</b>\n\n"
        "• <b>Interazione Libera:</b> Invia qualsiasi messaggio di testo normale per "
        "parlare con l'agente Antigravity nel workspace attivo. L'agente eseguirà i tuoi comandi.\n\n"
        "• <b>Caricamento File:</b> Trascina immagini o documenti per scaricarli direttamente in "
        "<code>telegram_uploads/</code> all'interno del workspace attivo. L'agente verrà avviato sul file.\n\n"
        "• <b>Elenco Comandi:</b>\n"
        "  /workspace - Gestisci la cartella di lavoro corrente (tastiera inline)\n"
        "  /workspace current - Mostra il percorso del workspace attivo\n"
        "  /model - Gestisci o imposta il modello della sessione\n"
        "  /new - Inizia una nuova conversazione pulita\n"
        "  /history - Mostra lo storico delle ultime 10 sessioni\n"
        "  /clear - Cancella la sessione dell'agente attiva\n"
        "  /status - Verifica lo stato di salute del bot e dell'agente\n"
        "  /stop - Interrompe l'elaborazione dell'agente in corso\n"
        "  /plan - Scarica l'ultimo implementation plan della sessione\n"
        "  /get &lt;percorso&gt; - Scarica un file specifico dal workspace\n"
        "  /help - Mostra questo messaggio"
    )
    await message.answer(help_text, parse_mode="HTML")
