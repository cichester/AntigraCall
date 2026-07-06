import logging
import datetime
from aiogram import Router, types
from aiogram.filters import Command
from antigracall.agent.manager import get_agent_manager

router = Router(name="admin")
logger = logging.getLogger("antigracall.bot.handlers.admin")

# Registra il tempo di caricamento del modulo (coincide con l'avvio del bot)
START_TIME = datetime.datetime.now()

def format_uptime(delta: datetime.timedelta) -> str:
    """Formatta la durata di uptime in una stringa leggibile."""
    seconds = int(delta.total_seconds())
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
        
    return " ".join(parts)

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Mostra lo stato del sistema e dell'agente."""
    try:
        manager = get_agent_manager()
        uptime_str = format_uptime(datetime.datetime.now() - START_TIME)
        
        # Determina lo stato del processo dell'agente
        if manager.current_process and manager.current_process.returncode is None:
            agent_status = "🟢 in esecuzione (elaborazione task)"
        else:
            agent_status = "💤 idle (in attesa di comandi)"
            
        ws_path = manager.current_workspace or "Nessuno"
        session_id = manager.current_session_id or "Nessuna"
        model_name = manager.current_model or "Default (CLI)"
        
        status_text = (
            "📊 <b>Stato AntigraCall</b>\n\n"
            f"├─ ⏱️ <b>Uptime bot:</b> <code>{uptime_str}</code>\n"
            f"├─ 🗂️ <b>Workspace attivo:</b> <code>{ws_path}</code>\n"
            f"├─ 💬 <b>ID Sessione:</b> <code>{session_id}</code>\n"
            f"├─ 🧠 <b>Modello attivo:</b> <code>{model_name}</code>\n"
            f"└─ 🤖 <b>Stato Agente:</b> <code>{agent_status}</code>"
        )
        await message.answer(status_text, parse_mode="HTML")
    except Exception as e:
        logger.exception(f"Errore durante /status: {e}")
        await message.answer(f"❌ Errore nel recupero dello stato:\n<code>{e}</code>")

@router.message(Command("stop"))
async def cmd_stop(message: types.Message):
    """Interrompe forzatamente il processo dell'agente in esecuzione."""
    try:
        manager = get_agent_manager()
        success = await manager.stop_current_task()
        if success:
            await message.answer("🛑 <b>Elaborazione dell'agente interrotta con successo!</b>", parse_mode="HTML")
        else:
            await message.answer("⚠️ Nessun task attivo dell'agente in corso da interrompere.")
    except Exception as e:
        logger.exception(f"Errore durante /stop: {e}")
        await message.answer(f"❌ Errore durante l'interruzione del task:\n<code>{e}</code>")
