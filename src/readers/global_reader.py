"""
Reader for global Cursor state database.

Extracts full composer conversations from globalStorage/state.vscdb
cursorDiskKV table where keys are binary-encoded "composerData:{uuid}".
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Iterator
from datetime import datetime
import platform

logger = logging.getLogger(__name__)


def get_cursor_global_storage_path() -> Path:
    """
    Get the path to Cursor global storage directory.
    
    Returns
    ----
    Path
        Path to globalStorage directory
    """
    home = Path.home()
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        return home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage"
    elif system == 'Windows':
        return Path(home) / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage"
    elif system == 'Linux':
        return home / ".config" / "Cursor" / "User" / "globalStorage"
    else:
        raise OSError(f"Unsupported operating system: {system}")


class GlobalComposerReader:
    """
    Reads full composer conversations from global Cursor database.
    
    The global database stores all composer data in cursorDiskKV table
    with binary-encoded keys in format "composerData:{uuid}".
    """
    
    def __init__(self, global_storage_path: Optional[Path] = None):
        """
        Initialize reader.
        
        Parameters
        ----
        global_storage_path : Path, optional
            Path to globalStorage directory. If None, uses default OS location.
        """
        if global_storage_path is None:
            global_storage_path = get_cursor_global_storage_path()
        self.global_storage_path = global_storage_path
        self.db_path = global_storage_path / "state.vscdb"
    
    def _decode_key(self, hex_key: bytes) -> Optional[str]:
        """
        Decode binary key to string.
        
        Parameters
        ----
        hex_key : bytes
            Binary key data
            
        Returns
        ----
        str
            Decoded key string, or None if decoding fails
        """
        try:
            # Keys are stored as hex-encoded strings
            if isinstance(hex_key, bytes):
                # Try to decode as UTF-8 first
                try:
                    return hex_key.decode('utf-8')
                except UnicodeDecodeError:
                    # If that fails, it might be hex-encoded
                    hex_str = hex_key.hex()
                    # Try to decode hex to string
                    return bytes.fromhex(hex_str).decode('utf-8')
            return str(hex_key)
        except Exception as e:
            logger.debug("Failed to decode key: %s", e)
            return None
    
    def _extract_composer_id_from_key(self, key: str) -> Optional[str]:
        """
        Extract composer UUID from decoded key.
        
        Parameters
        ----
        key : str
            Decoded key string (format: "composerData:{uuid}")
            
        Returns
        ----
        str
            Composer UUID, or None if not found
        """
        if key and key.startswith("composerData:"):
            return key[len("composerData:"):]
        return None
    
    def read_all_composers(self) -> Iterator[Dict[str, Any]]:
        """
        Read all composer conversations from global database.
        
        Yields
        ----
        Dict[str, Any]
            Composer data with decoded key and parsed conversation
        """
        if not self.db_path.exists():
            logger.warning("Global database does not exist: %s", self.db_path)
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Check if cursorDiskKV table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cursorDiskKV'")
            if not cursor.fetchone():
                logger.warning("cursorDiskKV table not found in global database")
                conn.close()
                return
            
            # Search for keys that start with "composerData:" 
            # Keys are stored as binary, so we need to search by hex pattern
            search_prefix = "composerData:".encode('utf-8')
            hex_prefix = search_prefix.hex()
            
            # Use hex() function to search
            cursor.execute("SELECT key, value FROM cursorDiskKV WHERE hex(key) LIKE ?", 
                          (f"{hex_prefix}%",))
            
            count = 0
            for row in cursor.fetchall():
                key_data = row[0]
                value_data = row[1]
                
                # Decode key
                decoded_key = self._decode_key(key_data)
                if not decoded_key:
                    continue
                
                composer_id = self._extract_composer_id_from_key(decoded_key)
                if not composer_id:
                    continue
                
                # Parse value (should be JSON)
                try:
                    if isinstance(value_data, bytes):
                        composer_data = json.loads(value_data.decode('utf-8'))
                    else:
                        composer_data = json.loads(value_data)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning("Failed to parse composer data for %s: %s", composer_id, e)
                    continue
                
                yield {
                    "composer_id": composer_id,
                    "key": decoded_key,
                    "data": composer_data,
                }
                count += 1
            
            conn.close()
            logger.info("Read %d composers from global database", count)
            
        except sqlite3.Error as e:
            logger.error("Error reading global database: %s", e)
    
    def read_composer(self, composer_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a specific composer by ID.
        
        Parameters
        ----
        composer_id : str
            Composer UUID
            
        Returns
        ----
        Dict[str, Any]
            Composer data, or None if not found
        """
        if not self.db_path.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Search for key containing this composer ID
            # Keys are binary, so we need to search by hex pattern
            search_pattern = f"composerData:{composer_id}".encode('utf-8')
            hex_pattern = search_pattern.hex()
            
            cursor.execute("SELECT key, value FROM cursorDiskKV WHERE hex(key) = ?", 
                          (hex_pattern,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            # Parse value
            value_data = row[1]
            try:
                if isinstance(value_data, bytes):
                    composer_data = json.loads(value_data.decode('utf-8'))
                else:
                    composer_data = json.loads(value_data)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning("Failed to parse composer data: %s", e)
                conn.close()
                return None
            
            conn.close()
            
            return {
                "composer_id": composer_id,
                "data": composer_data,
            }
            
        except sqlite3.Error as e:
            logger.error("Error reading composer %s: %s", composer_id, e)
            return None

