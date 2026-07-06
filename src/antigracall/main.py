import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from antigracall.utils.config import get_config
from antigracall.utils.logger import get_logger
from antigracall.bot.middlewares.auth import AuthMiddleware
from antigracall.bot.handlers import start, chat, workspace, session, admin, model
from antigracall.agent.manager import get_agent_manager

logger = logging.getLogger("antigracall.main")

async def on_startup(dispatcher: Dispatcher):
    """Callback all'avvio del bot."""
    logger.info("Avvio del bot Telegram...")
    # Inizializza l'AgentManager all'avvio ed aspetta il setup del DB
    manager = get_agent_manager()
    await manager.initialize()

async def on_shutdown(dispatcher: Dispatcher):
    """Callback allo spegnimento del bot."""
    logger.info("Bot arrestato con successo.")

async def main_async():
    # Inizializza config e logger
    config = get_config()
    get_logger()
    
    # Inizializza Bot e Dispatcher
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    
    # Registra eventi di ciclo di vita
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Registra middleware globale per i messaggi e le query
    dp.message.outer_middleware(AuthMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())
    
    # Registra i router
    dp.include_router(start.router)
    dp.include_router(workspace.router)
    dp.include_router(session.router)
    dp.include_router(model.router)
    dp.include_router(admin.router)
    dp.include_router(chat.router)
    
    # Avvia polling con recupero dagli errori di rete
    logger.info("Avvio polling di Telegram...")
    retry_delay = 5
    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except asyncio.CancelledError:
                logger.info("Polling cancellato.")
                break
            except Exception as e:
                logger.exception(f"Errore durante il polling di Telegram. Riprovo in {retry_delay}s: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(60, retry_delay * 2)
    finally:
        await bot.session.close()

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot interrotto dall'utente via tastiera.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Applicazione interrotta per un errore non gestito: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
