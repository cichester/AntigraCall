from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Tuple
from antigracall.utils.config import get_config

def get_workspace_categories_keyboard() -> InlineKeyboardMarkup:
    """Genera la tastiera con le categorie di workspace principali."""
    config = get_config()
    builder = InlineKeyboardBuilder()
    
    for idx, ws in enumerate(config.workspaces):
        builder.button(
            text=ws.name,
            callback_data=f"ws_cat:{idx}"
        )
    
    builder.button(text="❌ Annulla", callback_data="ws_cancel")
    builder.adjust(1) # Una colonna per riga
    return builder.as_markup()

def get_workspace_subfolders_keyboard(category_idx: int) -> InlineKeyboardMarkup:
    """Genera la tastiera con le sottocartelle della categoria scelta."""
    config = get_config()
    builder = InlineKeyboardBuilder()
    
    if category_idx >= len(config.workspaces):
        return get_workspace_categories_keyboard()
        
    ws_info = config.workspaces[category_idx]
    for idx, subfolder in enumerate(ws_info.subfolders):
        builder.button(
            text=subfolder,
            callback_data=f"ws_set:{category_idx}:{idx}"
        )
        
    builder.button(text="🔙 Indietro", callback_data="ws_back")
    builder.button(text="❌ Annulla", callback_data="ws_cancel")
    builder.adjust(2) # Due colonne per riga, tranne i bottoni di controllo
    return builder.as_markup()

def get_sessions_keyboard(sessions: List[Tuple[str, str, str]], active_session_id: str) -> InlineKeyboardMarkup:
    """Genera la tastiera per selezionare una sessione storica."""
    builder = InlineKeyboardBuilder()
    
    for session_id, ws_path, preview in sessions:
        # Prendi l'ultima parte del percorso come nome visualizzato (es. AntigraCall)
        ws_name = ws_path.split('\\')[-1].split('/')[-1]
        
        # Tronca la preview se troppo lunga
        preview_truncated = preview[:25] + "..." if len(preview) > 25 else preview
        
        # Mostra una spunta verde sulla sessione attiva
        status_prefix = "🟢 " if session_id == active_session_id else ""
        button_text = f"{status_prefix}[{ws_name}] {preview_truncated}"
        
        builder.button(
            text=button_text,
            callback_data=f"sess_switch:{session_id}"
        )
        
    builder.button(text="❌ Annulla", callback_data="sess_cancel")
    builder.adjust(1)
    return builder.as_markup()
