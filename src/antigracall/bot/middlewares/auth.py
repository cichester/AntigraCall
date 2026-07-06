import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from antigracall.utils.config import get_config

logger = logging.getLogger("antigracall.bot.auth")

class AuthMiddleware(BaseMiddleware):
    """Middleware per restringere l'accesso solo all'utente autorizzato."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        config = get_config()
        
        # Recupera l'ID utente dall'evento
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            
        if user_id is None:
            logger.warning(f"Evento ricevuto senza un utente valido: {type(event)}")
            return None
            
        # Verifica se l'utente è autorizzato
        if user_id != config.allowed_user_id:
            logger.warning(f"Tentativo di accesso non autorizzato dall'utente ID: {user_id}")
            
            # Se è un messaggio, rispondi con un avviso di sicurezza
            if isinstance(event, Message):
                await event.answer("⛔ Accesso non autorizzato. Questo bot è privato.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Non autorizzato.", show_alert=True)
                
            return None
            
        # Se autorizzato, prosegui con la catena di middleware/handler
        return await handler(event, data)
