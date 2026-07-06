import logging
import uuid
import os
from pathlib import Path
from aiogram import Router, types, F
from aiogram.filters import Command
from antigracall.agent.manager import get_agent_manager
from antigracall.bot.keyboards.inline import get_sessions_keyboard

router = Router(name="session")
logger = logging.getLogger("antigracall.bot.handlers.session")

@router.message(Command("new"))
async def cmd_new_session(message: types.Message):
    """Crea una nuova sessione conversazionale pulita."""
    try:
        manager = get_agent_manager()
        
        # Genera nuovo ID sessione
        new_session_id = str(uuid.uuid4())
        workspace_path = str(manager.current_workspace) if manager.current_workspace else str(manager.config.root_dir)
        
        # Salva nel database (disattivando le vecchie sessioni)
        await manager.db_repo.create_session(new_session_id, workspace_path)
        manager.current_session_id = new_session_id
        
        await message.answer(
            f"🆕 <b>Nuova sessione avviata!</b>\n\n"
            f"La conversazione precedente è stata archiviata.\n"
            f"📁 <b>Workspace attivo:</b> <code>{workspace_path}</code>\n"
            f"🆔 <b>ID Sessione:</b> <code>{new_session_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore durante /new: {e}")
        await message.answer(f"❌ Errore durante l'apertura della nuova sessione:\n<code>{e}</code>")

@router.message(Command("clear"))
async def cmd_clear_session(message: types.Message):
    """Cancella la sessione corrente dal DB e resetta il manager."""
    try:
        manager = get_agent_manager()
        current_id = manager.current_session_id
        
        if current_id:
            await manager.db_repo.delete_session(current_id)
            manager.current_session_id = None
            
        await message.answer(
            "🧹 <b>Sessione corrente cancellata con successo!</b>\n"
            "Il prossimo messaggio avvierà automaticamente una nuova sessione pulita.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore durante /clear: {e}")
        await message.answer(f"❌ Errore durante la cancellazione della sessione:\n<code>{e}</code>")

@router.message(Command("history"))
async def cmd_history(message: types.Message):
    """Mostra lo storico delle ultime 10 sessioni."""
    try:
        manager = get_agent_manager()
        sessions = await manager.db_repo.get_recent_sessions(limit=10)
        
        if not sessions:
            await message.answer("🗄️ Nessuna sessione presente nello storico.")
            return
            
        active_id = manager.current_session_id or ""
        reply_markup = get_sessions_keyboard(sessions, active_id)
        
        await message.answer(
            "🗄️ <b>Storico delle Sessioni:</b>\n"
            "Seleziona una sessione per ripristinare il contesto:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore durante /history: {e}")
        await message.answer(f"❌ Errore durante il recupero dello storico:\n<code>{e}</code>")

@router.message(Command("plan"))
async def cmd_get_plan(message: types.Message):
    """Recupera l'ultimo implementation plan associato alla sessione corrente."""
    try:
        manager = get_agent_manager()
        
        # 1. Controlla prima nel workspace attivo
        workspace_plan = manager.current_workspace / "implementation_plan.md" if manager.current_workspace else None
        if workspace_plan and workspace_plan.exists() and workspace_plan.is_file():
            found_path = workspace_plan
        else:
            # 2. Cerca nel brain l'implementation_plan.md modificato più di recente
            brain_dirs = [
                Path(os.path.expandvars(r"%USERPROFILE%\.gemini\antigravity-cli\brain")),
                Path(os.path.expandvars(r"%USERPROFILE%\.gemini\antigravity-ide\brain"))
            ]
            candidates = []
            for brain_dir in brain_dirs:
                if brain_dir.exists():
                    try:
                        for p in brain_dir.rglob("implementation_plan.md"):
                            if p.is_file():
                                candidates.append((p.stat().st_mtime, p))
                    except Exception:
                        pass
                        
            candidates.sort(key=lambda x: x[0], reverse=True)
            found_path = candidates[0][1] if candidates else None
            
        if not found_path:
            await message.answer("📭 Nessun <code>implementation_plan.md</code> trovato nel sistema.", parse_mode="HTML")
            return
            
        # Invia l'implementation plan
        await message.answer_document(
            document=types.FSInputFile(str(found_path)),
            caption="📝 <b>Implementation Plan corrente</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore durante /plan: {e}")
        await message.answer(f"❌ Errore durante il recupero del piano:\n<code>{e}</code>")

@router.callback_query(F.data.startswith("sess_switch:"))
async def cb_session_switch(callback: types.CallbackQuery):
    """Gestisce il cambio della sessione attiva tramite callback query."""
    try:
        session_id = callback.data.split(":")[1]
        manager = get_agent_manager()
        
        # Recupera dettagli sessione
        session = await manager.db_repo.get_session(session_id)
        if not session:
            await callback.answer("Sessione non trovata nel database.", show_alert=True)
            return
            
        # Attiva nel DB e in memoria
        await manager.db_repo.activate_session(session_id)
        manager.current_session_id = session_id
        manager.current_workspace = Path(session.workspace_path)
        
        ws_name = session.workspace_path.split('\\')[-1].split('/')[-1]
        
        await callback.message.edit_text(
            f"🟢 <b>Sessione ripristinata con successo!</b>\n\n"
            f"📁 <b>Workspace attivo:</b> <code>{session.workspace_path}</code>\n"
            f"🆔 <b>ID Sessione:</b> <code>{session_id}</code>",
            parse_mode="HTML"
        )
        await callback.answer(f"Sessione cambiata su {ws_name}")
    except Exception as e:
        logger.exception(f"Errore nella callback sess_switch: {e}")
        await callback.answer(f"Errore: {e}", show_alert=True)

@router.callback_query(F.data == "sess_cancel")
async def cb_session_cancel(callback: types.CallbackQuery):
    """Annulla la selezione ed elimina il messaggio."""
    await callback.message.delete()
    await callback.answer("Storico chiuso.")
