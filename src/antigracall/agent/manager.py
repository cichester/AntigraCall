import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional
from antigracall.utils.config import get_config
from antigracall.db.repository import DatabaseRepository

logger = logging.getLogger("antigracall.agent.manager")

# Path dell'eseguibile agy
AGY_BIN = Path(os.environ.get(
    "AGY_PATH",
    os.path.expandvars(r"%LOCALAPPDATA%\agy\bin\agy.exe")
))


class AgentManager:
    """Gestisce l'interazione con Antigravity CLI (`agy`)."""

    def __init__(self):
        self.config = get_config()
        self.current_workspace: Optional[Path] = None
        self.current_session_id: Optional[str] = None
        self.current_process: Optional[asyncio.subprocess.Process] = None
        self._was_interrupted = False
        self.db_repo = DatabaseRepository(self.config.db_path)

        # Imposta il workspace di default
        if self.config.default_workspace:
            self.current_workspace = Path(self.config.default_workspace)
        elif self.config.workspaces:
            ws = self.config.workspaces[0]
            if ws.subfolders:
                self.current_workspace = ws.get_subfolder_path(ws.subfolders[0])
            else:
                self.current_workspace = ws.path

        # Verifica che il binario agy esista
        if not AGY_BIN.exists():
            logger.error(
                f"Binario agy non trovato in: {AGY_BIN}. "
                "Installa la CLI con: irm https://antigravity.google/cli/install.ps1 | iex"
            )
        else:
            logger.info(f"Binario agy trovato: {AGY_BIN}")

        logger.info(f"AgentManager inizializzato. Workspace di default: {self.current_workspace}")

    async def initialize(self):
        """Inizializza il database e carica l'ultima sessione attiva, altrimenti ne crea una."""
        await self.db_repo.initialize()
        
        active_session = await self.db_repo.get_active_session()
        if active_session:
            self.current_session_id = active_session.id
            self.current_workspace = Path(active_session.workspace_path)
            logger.info(f"Ripristinata sessione attiva {self.current_session_id} in {self.current_workspace}")
        else:
            self.current_session_id = str(uuid.uuid4())
            await self.db_repo.create_session(self.current_session_id, str(self.current_workspace))
            logger.info(f"Nessuna sessione attiva trovata. Creata sessione {self.current_session_id} in {self.current_workspace}")

    async def send_message(self, text: str) -> tuple[str, list[Path]]:
        """Invia un messaggio all'agente Antigravity CLI e restituisce la risposta e i file modificati."""
        if not AGY_BIN.exists():
            return (
                "❌ Il binario `agy` non è stato trovato.\n"
                "Installa la CLI di Antigravity con:\n"
                "<code>irm https://antigravity.google/cli/install.ps1 | iex</code>",
                []
            )

        # Assicuriamoci che ci sia una sessione attiva prima di inviare
        if not self.current_session_id:
            self.current_session_id = str(uuid.uuid4())
            await self.db_repo.create_session(self.current_session_id, str(self.current_workspace))

        # Reset flag interruzione ad ogni invio
        self._was_interrupted = False

        # Salva messaggio utente nel DB
        await self.db_repo.add_message(self.current_session_id, 'user', text)

        # Istruisce l'agente a salvare i nuovi file per l'utente dentro telegram_uploads
        system_note = (
            "\n\n[NOTA: Se devi creare nuovi file o generare output/documenti da restituire all'utente, "
            "salvali all'interno della cartella 'telegram_uploads' del workspace. "
            "Modifica invece i file del codice sorgente esistenti nel loro percorso originale.]"
        )
        agent_prompt = text + system_note

        # Determina la directory di lavoro per l'agente
        cwd = str(self.current_workspace) if self.current_workspace else None

        # Costruisci gli argomenti della CLI per agy
        args = [
            str(AGY_BIN), "-p", agent_prompt,
            "--conversation", self.current_session_id,
            "--dangerously-skip-permissions"
        ]
        if cwd:
            args.extend(["--add-dir", cwd])

        logger.info(f"Invio messaggio all'agente (session_id={self.current_session_id}, cwd={cwd}): '{text[:80]}...'")

        # Scan del workspace prima di eseguire
        before_files = self._scan_workspace()

        try:
            # Esegui agy in modalità non-interattiva
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            self.current_process = process

            # Attendi il completamento con timeout
            timeout = self.config.settings.agent_timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            response = stdout.decode("utf-8", errors="replace").strip()

            if process.returncode != 0:
                stderr_text = stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"agy terminato con codice {process.returncode}: {stderr_text}")
                if self._was_interrupted:
                    response = "TASK_INTERRUPTED"
                elif not response:
                    response = f"❌ L'agente ha restituito un errore (codice {process.returncode}):\n<code>{stderr_text[:2000]}</code>"

            if not response:
                response = "⚠️ L'agente non ha prodotto alcun output."
            else:
                # Salva la risposta dell'agente nel DB se è andata a buon fine
                if not (response.startswith("❌") or response.startswith("⚠️") or response == "TASK_INTERRUPTED"):
                    await self.db_repo.add_message(self.current_session_id, 'agent', response)

            # Scan del workspace dopo l'esecuzione per trovare file nuovi o modificati
            after_files = self._scan_workspace()
            modified_files = []
            for filepath, mtime in after_files.items():
                if filepath not in before_files or mtime > before_files[filepath]:
                    modified_files.append(Path(filepath))

            logger.info(f"Risposta ricevuta ({len(response)} caratteri). Trovati {len(modified_files)} file modificati.")
            return response, modified_files

        except asyncio.TimeoutError:
            logger.error(f"Timeout dopo {timeout}s durante l'esecuzione dell'agente.")
            # Termina il processo se ancora in esecuzione
            try:
                process.kill()
            except Exception:
                pass
            return f"⏱️ L'agente ha superato il tempo limite ({timeout}s). Prova un comando più semplice o aumenta il timeout.", []

        except Exception as e:
            logger.exception(f"Errore durante l'esecuzione dell'agente: {e}")
            return f"❌ Errore di sistema:\n<code>{e}</code>", []
        
        finally:
            self.current_process = None

    def _scan_workspace(self) -> dict[str, float]:
        """Scansiona la cartella telegram_uploads del workspace e l'implementation plan."""
        files = {}
        
        # 1. Scansiona telegram_uploads nel workspace
        if self.current_workspace and self.current_workspace.exists():
            upload_dir = self.current_workspace / "telegram_uploads"
            if upload_dir.exists():
                try:
                    for path in upload_dir.rglob("*"):
                        if path.is_file():
                            files[str(path)] = path.stat().st_mtime
                except Exception as e:
                    logger.error(f"Errore durante la scansione di telegram_uploads: {e}")
                    
            # 2. Controlla implementation_plan.md nel workspace
            workspace_plan = self.current_workspace / "implementation_plan.md"
            if workspace_plan.exists() and workspace_plan.is_file():
                try:
                    files[str(workspace_plan)] = workspace_plan.stat().st_mtime
                except Exception:
                    pass

        # 3. Scansiona tutti gli implementation_plan.md nelle cartelle brain (CLI e IDE)
        brain_dirs = [
            Path(os.path.expandvars(r"%USERPROFILE%\.gemini\antigravity-cli\brain")),
            Path(os.path.expandvars(r"%USERPROFILE%\.gemini\antigravity-ide\brain"))
        ]
        for brain_dir in brain_dirs:
            if brain_dir.exists():
                try:
                    for path in brain_dir.rglob("implementation_plan.md"):
                        if path.is_file():
                            files[str(path)] = path.stat().st_mtime
                except Exception as e:
                    logger.debug(f"Errore nella scansione della cartella brain {brain_dir}: {e}")
                
        return files

    async def stop_current_task(self) -> bool:
        """Termina il processo dell'agente attivo, se in esecuzione."""
        if self.current_process and self.current_process.returncode is None:
            try:
                self._was_interrupted = True
                self.current_process.kill()
                logger.info("Processo dell'agente interrotto con successo.")
                return True
            except Exception as e:
                logger.error(f"Errore durante l'interruzione del processo dell'agente: {e}")
        return False

    async def set_workspace(self, workspace_path: Path):
        """Cambia il workspace corrente."""
        if not workspace_path.exists():
            raise ValueError(f"Il percorso non esiste: {workspace_path}")
        self.current_workspace = workspace_path
        if self.current_session_id:
            await self.db_repo.update_session_workspace(self.current_session_id, str(workspace_path))
        logger.info(f"Workspace cambiato a: {workspace_path}")


# Singleton
_agent_manager_instance: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    global _agent_manager_instance
    if _agent_manager_instance is None:
        _agent_manager_instance = AgentManager()
    return _agent_manager_instance
