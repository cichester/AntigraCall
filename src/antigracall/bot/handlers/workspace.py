import logging
from pathlib import Path
from aiogram import Router, types, F
from aiogram.filters import Command
from antigracall.agent.manager import get_agent_manager
from antigracall.utils.config import get_config
from antigracall.bot.keyboards.inline import (
    get_workspace_categories_keyboard,
    get_workspace_subfolders_keyboard
)

router = Router(name="workspace")
logger = logging.getLogger("antigracall.bot.handlers.workspace")

@router.message(Command("workspace"))
async def cmd_workspace(message: types.Message):
    """Gestisce il comando /workspace."""
    args = message.text.split(maxsplit=1)
    manager = get_agent_manager()
    
    if len(args) > 1:
        subcommand = args[1].strip().lower()
        if subcommand in ("current", "info", "show"):
            ws_path = manager.current_workspace
            if ws_path:
                await message.answer(
                    f"🗂️ <b>Workspace Attivo:</b>\n"
                    f"<code>{ws_path}</code>",
                    parse_mode="HTML"
                )
            else:
                await message.answer("⚠️ Nessun workspace attivo impostato al momento.")
            return
            
    # Se non c'è sotto-comando, mostra la tastiera inline di selezione
    await message.answer(
        "📂 <b>Seleziona un'area di lavoro:</b>\n"
        "Scegli una categoria principale:",
        reply_markup=get_workspace_categories_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("ws_cat:"))
async def cb_workspace_category(callback: types.CallbackQuery):
    """Gestisce il cambio categoria nella tastiera inline."""
    try:
        category_idx = int(callback.data.split(":")[1])
        config = get_config()
        if category_idx >= len(config.workspaces):
            await callback.answer("Categoria non valida", show_alert=True)
            return
            
        ws_info = config.workspaces[category_idx]
        await callback.message.edit_text(
            f"📂 <b>{ws_info.name}</b>\n"
            f"Scegli una sottocartella come workspace attivo:",
            reply_markup=get_workspace_subfolders_keyboard(category_idx),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        logger.exception(f"Errore nella callback ws_cat: {e}")
        await callback.answer("Errore nel caricamento delle sottocartelle.", show_alert=True)

@router.callback_query(F.data == "ws_back")
async def cb_workspace_back(callback: types.CallbackQuery):
    """Ritorna alla selezione delle categorie principali."""
    await callback.message.edit_text(
        "📂 <b>Seleziona un'area di lavoro:</b>\n"
        "Scegli una categoria principale:",
        reply_markup=get_workspace_categories_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "ws_cancel")
async def cb_workspace_cancel(callback: types.CallbackQuery):
    """Annulla la selezione ed elimina il messaggio."""
    await callback.message.delete()
    await callback.answer("Selezione annullata.")

@router.callback_query(F.data.startswith("ws_set:"))
async def cb_workspace_set(callback: types.CallbackQuery):
    """Imposta definitivamente il workspace selezionato."""
    try:
        parts = callback.data.split(":")
        category_idx = int(parts[1])
        folder_idx = int(parts[2])
        
        config = get_config()
        if category_idx >= len(config.workspaces):
            await callback.answer("Selezione non valida", show_alert=True)
            return
            
        ws_info = config.workspaces[category_idx]
        if folder_idx >= len(ws_info.subfolders):
            await callback.answer("Sottocartella non valida", show_alert=True)
            return
            
        folder_name = ws_info.subfolders[folder_idx]
        target_path = ws_info.get_subfolder_path(folder_name)
        
        manager = get_agent_manager()
        await manager.set_workspace(target_path)
        
        await callback.message.edit_text(
            f"✅ <b>Workspace aggiornato con successo!</b>\n\n"
            f"📁 <b>Directory attiva:</b>\n"
            f"<code>{target_path}</code>",
            parse_mode="HTML"
        )
        await callback.answer(f"Workspace impostato su {folder_name}")
    except Exception as e:
        logger.exception(f"Errore nella callback ws_set: {e}")
        await callback.answer(f"Errore: {e}", show_alert=True)
