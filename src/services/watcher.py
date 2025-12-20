"""
File watcher service for automatic incremental ingestion.

Monitors Cursor database files for changes and triggers incremental ingestion
when new chats are detected.
"""
import logging
import time
import os
from pathlib import Path
from typing import Optional, Callable, List
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from src.core.config import get_cursor_workspace_storage_path, get_cursor_global_storage_path

logger = logging.getLogger(__name__)


class CursorDatabaseHandler(FileSystemEventHandler):
    """
    File system event handler for Cursor database changes.
    
    Triggers ingestion callback when database files are modified.
    """
    
    def __init__(self, ingestion_callback: Callable[[], None], debounce_seconds: float = 5.0):
        """
        Initialize handler.
        
        Parameters
        ----
        ingestion_callback : Callable
            Function to call when ingestion should be triggered
        debounce_seconds : float
            Seconds to wait after last change before triggering (default: 5.0)
        """
        super().__init__()
        self.ingestion_callback = ingestion_callback
        self.debounce_seconds = debounce_seconds
        self.last_event_time = {}
        self._pending_timer = None
    
    def _should_process(self, file_path: str) -> bool:
        """
        Check if file path should trigger ingestion.
        
        Parameters
        ----
        file_path : str
            Path to changed file
            
        Returns
        ----
        bool
            True if file should trigger ingestion
        """
        path = Path(file_path)
        # Only watch state.vscdb files
        if path.name != "state.vscdb":
            return False
        
        # Check if it's in workspaceStorage or globalStorage
        workspace_path = get_cursor_workspace_storage_path()
        global_path = get_cursor_global_storage_path()
        
        try:
            resolved = path.resolve()
            workspace_resolved = workspace_path.resolve()
            global_resolved = global_path.resolve()
            
            return (str(resolved).startswith(str(workspace_resolved)) or
                    str(resolved).startswith(str(global_resolved)))
        except (OSError, ValueError):
            return False
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if self._should_process(event.src_path):
            self._schedule_ingestion()
    
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if self._should_process(event.src_path):
            self._schedule_ingestion()
    
    def _schedule_ingestion(self):
        """Schedule ingestion after debounce period."""
        import threading
        
        # Cancel existing timer if any
        if self._pending_timer:
            self._pending_timer.cancel()
        
        # Schedule new ingestion
        self._pending_timer = threading.Timer(
            self.debounce_seconds,
            self._trigger_ingestion
        )
        self._pending_timer.daemon = True
        self._pending_timer.start()
        logger.debug("Scheduled ingestion in %.1f seconds", self.debounce_seconds)
    
    def _trigger_ingestion(self):
        """Trigger the ingestion callback."""
        logger.info("Database change detected, triggering incremental ingestion...")
        try:
            self.ingestion_callback()
        except Exception as e:
            logger.error("Error during automatic ingestion: %s", e)


class PollingWatcher:
    """
    Polling-based watcher for systems without watchdog support.
    
    Checks database file modification times periodically.
    """
    
    def __init__(self, ingestion_callback: Callable[[], None], poll_interval: float = 30.0):
        """
        Initialize polling watcher.
        
        Parameters
        ----
        ingestion_callback : Callable
            Function to call when ingestion should be triggered
        poll_interval : float
            Seconds between polls (default: 30.0)
        """
        self.ingestion_callback = ingestion_callback
        self.poll_interval = poll_interval
        self.workspace_path = get_cursor_workspace_storage_path()
        self.global_path = get_cursor_global_storage_path()
        self.last_mtimes = {}
        self._running = False
    
    def _get_database_files(self) -> List[Path]:
        """Get all state.vscdb files to monitor."""
        files = []
        
        # Workspace databases
        if self.workspace_path.exists():
            for workspace_dir in self.workspace_path.iterdir():
                if workspace_dir.is_dir():
                    db_file = workspace_dir / "state.vscdb"
                    if db_file.exists():
                        files.append(db_file)
        
        # Global database
        global_db = self.global_path / "state.vscdb"
        if global_db.exists():
            files.append(global_db)
        
        return files
    
    def _check_changes(self) -> bool:
        """
        Check if any database files have changed.
        
        Returns
        ----
        bool
            True if changes detected
        """
        changed = False
        
        for db_file in self._get_database_files():
            try:
                current_mtime = db_file.stat().st_mtime
                file_key = str(db_file)
                
                if file_key in self.last_mtimes:
                    if current_mtime > self.last_mtimes[file_key]:
                        logger.debug("Detected change in %s", db_file)
                        changed = True
                else:
                    # First time seeing this file
                    changed = True
                
                self.last_mtimes[file_key] = current_mtime
            except (OSError, ValueError) as e:
                logger.debug("Error checking %s: %s", db_file, e)
        
        return changed
    
    def start(self):
        """Start polling loop."""
        import threading
        
        self._running = True
        
        def poll_loop():
            logger.info("Starting polling watcher (interval: %.1f seconds)", self.poll_interval)
            
            while self._running:
                try:
                    if self._check_changes():
                        logger.info("Database change detected, triggering incremental ingestion...")
                        try:
                            self.ingestion_callback()
                        except Exception as e:
                            logger.error("Error during automatic ingestion: %s", e)
                    
                    time.sleep(self.poll_interval)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error("Error in polling loop: %s", e)
                    time.sleep(self.poll_interval)
        
        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop polling."""
        self._running = False


class IngestionWatcher:
    """
    High-level watcher service that manages automatic incremental ingestion.
    
    Supports both file system events (via watchdog) and polling fallback.
    """
    
    def __init__(self, ingestion_callback: Callable[[], None],
                 use_watchdog: Optional[bool] = None,
                 debounce_seconds: float = 5.0,
                 poll_interval: float = 30.0):
        """
        Initialize watcher.
        
        Parameters
        ----
        ingestion_callback : Callable
            Function to call for incremental ingestion
        use_watchdog : bool, optional
            Force use of watchdog (True) or polling (False). If None, auto-detect.
        debounce_seconds : float
            Debounce time for watchdog events (default: 5.0)
        poll_interval : float
            Poll interval for polling mode (default: 30.0)
        """
        self.ingestion_callback = ingestion_callback
        self.debounce_seconds = debounce_seconds
        self.poll_interval = poll_interval
        
        # Auto-detect if watchdog should be used
        if use_watchdog is None:
            use_watchdog = WATCHDOG_AVAILABLE
        
        self.use_watchdog = use_watchdog
        self.observer = None
        self.polling_watcher = None
    
    def start(self):
        """Start watching for changes."""
        if self.use_watchdog and WATCHDOG_AVAILABLE:
            logger.info("Starting file system watcher (watchdog)...")
            handler = CursorDatabaseHandler(
                self.ingestion_callback,
                debounce_seconds=self.debounce_seconds
            )
            
            self.observer = Observer()
            
            # Watch workspace storage
            workspace_path = get_cursor_workspace_storage_path()
            if workspace_path.exists():
                self.observer.schedule(handler, str(workspace_path), recursive=True)
                logger.info("Watching workspace storage: %s", workspace_path)
            
            # Watch global storage
            global_path = get_cursor_global_storage_path()
            if global_path.exists():
                self.observer.schedule(handler, str(global_path), recursive=True)
                logger.info("Watching global storage: %s", global_path)
            
            self.observer.start()
            logger.info("File system watcher started")
        else:
            if self.use_watchdog:
                logger.warning("watchdog not available, falling back to polling")
            logger.info("Starting polling watcher...")
            self.polling_watcher = PollingWatcher(
                self.ingestion_callback,
                poll_interval=self.poll_interval
            )
            self.polling_watcher.start()
    
    def stop(self):
        """Stop watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("File system watcher stopped")
        
        if self.polling_watcher:
            self.polling_watcher.stop()
            self.polling_watcher = None
            logger.info("Polling watcher stopped")
    
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return (self.observer is not None and self.observer.is_alive()) or \
               (self.polling_watcher is not None and self.polling_watcher._running)

