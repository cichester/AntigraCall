import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from antigracall.agent.manager import get_agent_manager
from antigracall.bot.keyboards.inline import get_models_keyboard

router = Router(name="model")
logger = logging.getLogger("antigracall.bot.handlers.model")

@router.message(Command("model"))
async def cmd_model(message: types.Message):
    """Gestisce il comando /model."""
    args = message.text.split(maxsplit=1)
    manager = get_agent_manager()
    
    if len(args) > 1:
        # Imposta direttamente il modello specificato
        model_name = args[1].strip()
        if model_name.lower() in ("default", "none", "reset", "clear"):
            await manager.set_model(None)
            await message.answer("🔄 <b>Modello reimpostato su Default (CLI).</b>", parse_mode="HTML")
        else:
            await manager.set_model(model_name)
            await message.answer(f"✅ <b>Modello impostato su:</b> <code>{model_name}</code>", parse_mode="HTML")
        return
        
    # Senza parametri: mostra la tastiera inline di selezione
    # Invia prima un messaggio di caricamento se la chiamata dinamica potesse richiedere tempo
    status_msg = await message.answer("🔍 <i>Recupero modelli disponibili...</i>", parse_mode="HTML")
    try:
        models = await manager.get_available_models(force_refresh=False)
        reply_markup = get_models_keyboard(models, manager.current_model)
        await status_msg.edit_text(
            "🧠 <b>Seleziona il modello per l'agente:</b>\n"
            "Scegli un modello dall'elenco o imposta Default.",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore durante cmd_model: {e}")
        await status_msg.edit_text(f"❌ Errore nel recupero della lista dei modelli:\n<code>{e}</code>", parse_mode="HTML")

@router.callback_query(F.data.startswith("model_set:"))
async def cb_model_set(callback: types.CallbackQuery):
    """Callback di impostazione del modello."""
    try:
        model_id = callback.data.split(":", 1)[1]
        manager = get_agent_manager()
        
        if model_id == "default":
            await manager.set_model(None)
            display_name = "Default (CLI)"
        else:
            await manager.set_model(model_id)
            display_name = model_id
            
        await callback.message.edit_text(
            f"✅ <b>Modello aggiornato con successo!</b>\n\n"
            f"🧠 <b>Attivo:</b> <code>{display_name}</code>",
            parse_mode="HTML"
        )
        await callback.answer(f"Modello impostato su {display_name}")
    except Exception as e:
        logger.exception(f"Errore nella callback model_set: {e}")
        await callback.answer(f"Errore: {e}", show_alert=True)

@router.callback_query(F.data == "model_refresh")
async def cb_model_refresh(callback: types.CallbackQuery):
    """Callback per forzare il refresh dinamico dei modelli dalla CLI."""
    try:
        await callback.answer("Aggiornamento lista modelli in corso...")
        await callback.message.edit_text("🔄 <i>Aggiornamento lista modelli dalla CLI...</i>", parse_mode="HTML")
        
        manager = get_agent_manager()
        models = await manager.get_available_models(force_refresh=True)
        reply_markup = get_models_keyboard(models, manager.current_model)
        
        await callback.message.edit_text(
            "🧠 <b>Seleziona il modello per l'agente:</b>\n"
            "Elenco aggiornato con successo dalla CLI.",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore nella callback model_refresh: {e}")
        await callback.answer(f"Errore di aggiornamento: {e}", show_alert=True)

@router.callback_query(F.data == "model_cancel")
async def cb_model_cancel(callback: types.CallbackQuery):
    """Annulla la selezione ed elimina il messaggio."""
    await callback.message.delete()
    await callback.answer("Selezione annullata.")
