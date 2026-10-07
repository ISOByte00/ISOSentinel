"""
YKS Sentinel — Autonomous Study Guardian (v0.1 MVP)
Main Bootstrap Entry Point.
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from config.settings import settings
from database.database import DatabaseManager
from app.application import SentinelMainWindow


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger("main")
    logger.info(f"Starting {settings.app_name} v{settings.version}...")

    # 1. Initialize SQLite Database & Schema
    db_manager = DatabaseManager(settings.db_path)
    db_manager.initialize()

    # 2. Start Qt Application
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(settings.app_name)

    # 3. Create & Launch Main Window
    window = SentinelMainWindow(db_manager)
    window.show()

    # 4. Exec Loop
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()