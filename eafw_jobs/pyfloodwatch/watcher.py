"""File watcher - monitors directory for new GeoJSON files and ingests them"""
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .settings import DATA_DIR
from .logger_config import setup_logger

logger = setup_logger(__name__, 'watcher.log')


class GeoJSONHandler(FileSystemEventHandler):
    """Handles new GeoJSON file events"""

    def on_created(self, event):
        """Called when a file is created"""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Only process GeoJSON files
        if filepath.suffix.lower() != '.geojson':
            return

        logger.info(f"New file detected: {filepath.name}")

        # Add processing logic here if needed
        # For now, files are processed by the download service


def main():
    """Main watcher loop"""
    watch_dir = DATA_DIR / 'download'
    watch_dir.mkdir(parents=True, exist_ok=True)

    logger.info("FloodWatch Jobs - File Watcher Started")
    logger.info(f"Watching directory: {watch_dir}")

    event_handler = GeoJSONHandler()
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
