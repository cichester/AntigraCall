import asyncio
import logging
import datetime
from aiogram import Router, types, F, Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from antigracall.agent.manager import get_agent_manager
from antigracall.agent.formatter import markdown_to_html
from antigracall.utils.config import get_config

router = Router(name="chat")
logger = logging.getLogger("antigracall.bot.chat")

async def keep_typing(bot: Bot, chat_id: int, stop_event: asyncio.Event):
    """Invia l'indicatore di typing a intervalli regolari finché non viene fermato."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4.5)  # Telegram nasconde l'azione dopo 5 secondi
        except Exception as e:
            logger.debug(f"Errore durante l'invio del typing indicator: {e}")
            break

async def monitor_agent_execution(message: types.Message, stop_event: asyncio.Event):
    """Monitora il tempo trascorso per task lunghi e notifica l'utente con barra di progresso."""
    elapsed = 0
    status_msg = None
    
    # Aspetta 15 secondi prima di mostrare la barra di progresso
    while elapsed < 15:
        if stop_event.is_set():
            return
        await asyncio.sleep(1)
        elapsed += 1
        
    if stop_event.is_set():
        return

    # Pulsante inline per forzare lo stop del subprocess
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛑 Interrompi", callback_data="task_stop")
    ]])
    
    # Testo personalizzato richiesto dall'utente
    base_text = (
        "⏳ <b>L'agente ci sta mettendo un po', rilassati, ti avvertirò quando l'esecuzione è terminata</b>\n\n"
        "Progresso: "
    )
    
    try:
        status_msg = await message.answer(
            f"{base_text}<code>[░░░░░░░░░░] (15s)</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Errore durante l'invio del progresso iniziale: {e}")
        
    # Aggiorna progress bar ogni 5 secondi
    while not stop_event.is_set() and status_msg:
        await asyncio.sleep(5)
        elapsed += 5
        
        # Progression rate fittizia fino al 95%
        progress_pct = min(95, int((elapsed / 60) * 100))
        filled = progress_pct // 10
        bar = "█" * filled + "░" * (10 - filled)
        
        try:
            await status_msg.edit_text(
                f"{base_text}<code>[{bar}] {progress_pct}% ({elapsed}s)</code>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass # Ignora se modificato altrove o cancellato
            
    # Pulisce la barra di caricamento
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass

@router.callback_query(F.data == "task_stop")
async def cb_task_stop(callback: types.CallbackQuery):
    """Gestisce l'interruzione della CLI su richiesta dell'utente."""
    manager = get_agent_manager()
    success = await manager.stop_current_task()
    if success:
        await callback.message.edit_text("🛑 <b>Elaborazione interrotta dall'utente.</b>", parse_mode="HTML")
        await callback.answer("Interruzione eseguita con successo.")
    else:
        await callback.answer("Nessuna elaborazione attiva da interrompere.", show_alert=True)

def split_message(text: str, max_length: int) -> list[str]:
    """Splitta il testo in blocchi di dimensione massima rispettando i tag HTML."""
    # Semplice split per righe per evitare di rompere tag HTML a metà riga
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        # Se una singola riga supera il limite, la spezziamo forzatamente
        if len(line) > max_length:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            # Spezza la riga
            for i in range(0, len(line), max_length):
                chunks.append(line[i:i+max_length])
            continue
            
        if current_length + len(line) + 1 > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

async def execute_agent_and_reply(message: types.Message, prompt_text: str):
    """Esegue l'agente col prompt dato, gestisce typing, progresso, e risponde con testo e file modificati."""
    # Avvia l'indicatore di typing in background
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(message.bot, message.chat.id, stop_event))
    
    # Avvia il monitoraggio proattivo
    monitor_task = asyncio.create_task(monitor_agent_execution(message, stop_event))

    response_text = ""
    modified_files = []
    
    try:
        # Ottieni la risposta dall'agente
        agent_manager = get_agent_manager()
        response_text, modified_files = await agent_manager.send_message(prompt_text)
    finally:
        # Ferma l'indicatore di typing e il monitoraggio
        stop_event.set()
        await typing_task
        await monitor_task

    # Se la risposta indica un task interrotto, esci silenziosamente
    if response_text == "TASK_INTERRUPTED":
        return

    # Se la risposta è vuota o di errore, non formattare
    if response_text.startswith("❌") or response_text.startswith("⚠️") or response_text.startswith("⏱️"):
        await message.answer(response_text, parse_mode="HTML")
        return

    config = get_config()
    max_len = config.settings.max_message_length
    threshold = config.settings.code_file_threshold

    # Caso 1: La risposta è molto lunga -> Inviala come file Markdown allegato
    if len(response_text) > threshold:
        logger.info(f"Risposta molto lunga ({len(response_text)} char). Invio come file .md.")
        file_data = response_text.encode("utf-8")
        input_file = BufferedInputFile(file_data, filename="risposta_agente.md")
        await message.answer_document(
            document=input_file,
            caption="📄 La risposta dell'agente è troppo lunga per la chat ed è stata allegata come file Markdown."
        )
    else:
        # Formatta il testo in HTML compatibile con Telegram
        formatted_html = markdown_to_html(response_text)

        # Caso 2: La risposta formattata rientra nei limiti di un singolo messaggio
        if len(formatted_html) <= max_len:
            try:
                await message.answer(formatted_html, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Errore durante l'invio dell'HTML formattato: {e}")
                # Fallback al testo non formattato in caso di errore di parsing HTML
                await message.answer(response_text)
        else:
            # Caso 3: Splitting in blocchi
            chunks = split_message(formatted_html, max_len)
            for idx, chunk in enumerate(chunks):
                try:
                    await message.answer(f"[Parte {idx+1}/{len(chunks)}]\n{chunk}", parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Errore invio chunk {idx+1}: {e}")
                    raw_chunks = split_message(response_text, max_len)
                    await message.answer(f"[Parte {idx+1}/{len(raw_chunks)}]\n{raw_chunks[idx]}")

    # Invia gli eventuali file modificati o creati dall'agente
    for file_path in modified_files:
        try:
            if not file_path.exists() or not file_path.is_file():
                continue
                
            ext = file_path.suffix.lower()
            input_file = types.FSInputFile(str(file_path))
            
            if ext in (".png", ".jpg", ".jpeg", ".webp"):
                await message.answer_photo(
                    photo=input_file,
                    caption=f"🖼️ Immagine generata/modificata: <code>{file_path.name}</code>",
                    parse_mode="HTML"
                )
            else:
                await message.answer_document(
                    document=input_file,
                    caption=f"📄 File generato/modificato: <code>{file_path.name}</code>",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Errore nell'invio del file modificato {file_path.name}: {e}")

@router.message(F.text & ~F.text.startswith("/"))
async def handle_chat_message(message: types.Message):
    """Gestisce i messaggi di testo inoltrandoli ad Antigravity."""
    user_text = message.text
    if not user_text:
        return
    await execute_agent_and_reply(message, user_text)

@router.message(F.document | F.photo)
async def handle_user_files(message: types.Message):
    """Gestisce i file e le immagini caricate dall'utente, salvandoli nel workspace."""
    if not message.bot:
        return
        
    try:
        manager = get_agent_manager()
        workspace = manager.current_workspace or manager.config.root_dir
        
        file_id = ""
        file_name = ""
        
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or f"document_{int(asyncio.get_event_loop().time())}"
        elif message.photo:
            photo_size = message.photo[-1]
            file_id = photo_size.file_id
            file_name = f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
        # Crea la cartella ad hoc telegram_uploads nel workspace
        upload_dir = workspace / "telegram_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = upload_dir / file_name
        
        # Scarica il file nel workspace
        file = await message.bot.get_file(file_id)
        await message.bot.download_file(file.file_path, str(dest_path))
        
        logger.info(f"File scaricato nel workspace in: {dest_path}")
        
        caption_text = message.caption or "Analizza questo file."
        prompt = (
            f"[File Ricevuto: {file_name}]\n"
            f"Ho salvato questo file nel workspace in: <code>{dest_path}</code>.\n\n"
            f"Richiesta dell'utente: {caption_text}"
        )
        
        await message.answer(
            f"📥 <b>File scaricato nel workspace!</b>\n"
            f"📁 Percorso: <code>telegram_uploads/{file_name}</code>\n"
            "Elaborazione dell'agente avviata...",
            parse_mode="HTML"
        )
        
        await execute_agent_and_reply(message, prompt)
        
    except Exception as e:
        logger.exception(f"Errore durante l'upload del file: {e}")
        await message.answer(f"❌ Errore durante l'acquisizione del file:\n<code>{e}</code>")

@router.message(Command("get"))
async def cmd_get_file(message: types.Message):
    """Consente all'utente di richiedere e scaricare un file specifico dal workspace."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Specifica il percorso del file. Esempio: <code>/get src/main.py</code>", parse_mode="HTML")
        return
        
    file_rel_path = args[1].strip()
    manager = get_agent_manager()
    workspace = manager.current_workspace or manager.config.root_dir
    
    try:
        target_path = (workspace / file_rel_path).resolve()
        
        # Controlla esistenza e tipo
        if not target_path.exists():
            await message.answer(f"❌ Il file <code>{file_rel_path}</code> non esiste nel workspace.", parse_mode="HTML")
            return
            
        if not target_path.is_file():
            await message.answer(f"❌ <code>{file_rel_path}</code> non è un file valido.", parse_mode="HTML")
            return
            
        # Controllo Directory Traversal
        if not str(target_path).startswith(str(workspace.resolve())):
            await message.answer("❌ Non sei autorizzato a scaricare file fuori dal workspace corrente.", parse_mode="HTML")
            return
            
        # Invia il file
        await message.answer_document(
            document=types.FSInputFile(str(target_path)),
            caption=f"📄 File: <code>{file_rel_path}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Errore durante /get: {e}")
        await message.answer(f"❌ Errore durante l'invio del file:\n<code>{e}</code>")

def escape_plain_text(text: str) -> str:
    """Metodo di utility per sanitizzare il testo semplice in HTML."""
    import html
    return html.escape(text)
