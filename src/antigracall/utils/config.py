import os
from pathlib import Path
from typing import Dict, List, Any
import yaml
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

class ConfigError(Exception):
    """Errore durante il caricamento o la validazione della configurazione."""
    pass

class Settings:
    def __init__(self, data: Dict[str, Any]):
        self.agent_timeout = int(data.get("bot", {}).get("agent_timeout", 120))
        self.max_message_length = int(data.get("bot", {}).get("max_message_length", 4000))
        self.code_file_threshold = int(data.get("bot", {}).get("code_file_threshold", 6000))
        self.log_level = data.get("logging", {}).get("level", "INFO")
        self.log_file = data.get("logging", {}).get("file", "antigracall.log")
        self.log_max_bytes = int(data.get("logging", {}).get("max_bytes", 10485760))
        self.log_backup_count = int(data.get("logging", {}).get("backup_count", 5))
        self.skills_paths = data.get("skills", {}).get("paths", [])

class WorkspaceInfo:
    def __init__(self, name: str, path: str, subfolders: List[str]):
        self.name = name
        self.path = Path(path)
        self.subfolders = subfolders

    def get_subfolder_path(self, subfolder: str) -> Path:
        if subfolder not in self.subfolders:
            raise ValueError(f"Sottocartella '{subfolder}' non configurata per {self.name}")
        return self.path / subfolder

class Config:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.config_dir = root_dir / "config"
        
        # Carica variabili ambiente
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        allowed_user_id_str = os.getenv("TELEGRAM_ALLOWED_USER_ID")
        self.allowed_user_id = int(allowed_user_id_str) if allowed_user_id_str else None
        self.default_workspace = os.getenv("ANTIGRAVITY_DEFAULT_WORKSPACE")
        self.db_path = self.root_dir / "db" / "antigracall.db"
        
        # Validazione variabili essenziali
        if not self.bot_token:
            raise ConfigError("Variabile d'ambiente TELEGRAM_BOT_TOKEN mancante!")
        if self.allowed_user_id is None:
            raise ConfigError("Variabile d'ambiente TELEGRAM_ALLOWED_USER_ID mancante o non valida!")
            
        # Carica file yaml
        self.settings = self._load_settings()
        self.workspaces = self._load_workspaces()

    def _load_settings(self) -> Settings:
        file_path = self.config_dir / "settings.yaml"
        if not file_path.exists():
            # Defaults se il file non esiste
            return Settings({})
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return Settings(data)
        except Exception as e:
            raise ConfigError(f"Impossibile leggere settings.yaml: {e}")

    def _load_workspaces(self) -> List[WorkspaceInfo]:
        file_path = self.config_dir / "workspaces.yaml"
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                workspaces_data = data.get("workspaces", [])
                
                workspaces = []
                for ws in workspaces_data:
                    name = ws.get("name")
                    path = ws.get("path")
                    subfolders = ws.get("subfolders", [])
                    if not name or not path:
                        continue
                    workspaces.append(WorkspaceInfo(name, path, subfolders))
                return workspaces
        except Exception as e:
            raise ConfigError(f"Impossibile leggere workspaces.yaml: {e}")

# Singleton globale
_config_instance = None

def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        # Trova la root del progetto (2 livelli sopra rispetto a questo file)
        root_dir = Path(__file__).parent.parent.parent.parent
        _config_instance = Config(root_dir)
    return _config_instance
