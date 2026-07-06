import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from antigracall.utils.config import get_config

def setup_logger():
    """Configura e restituisce il logger principale del progetto."""
    config = get_config()
    
    # Determina il percorso del file di log
    log_file_name = config.settings.log_file
    log_dir = config.root_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / log_file_name
    
    # Determina il livello di log
    level_str = config.settings.log_level.upper()
    level = getattr(logging, level_str, logging.INFO)
    
    # Formattatore
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler per file con rotazione
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.settings.log_max_bytes,
        backupCount=config.settings.log_backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    
    # Handler per console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Rimuovi eventuali handler esistenti
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Logger specifico del pacchetto
    logger = logging.getLogger("antigracall")
    logger.setLevel(level)
    
    logger.info("Logging configurato con successo!")
    logger.info(f"File log: {log_path}")
    logger.info(f"Livello log: {level_str}")
    
    return logger

# Singleton logger
_logger = None

def get_logger():
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger
