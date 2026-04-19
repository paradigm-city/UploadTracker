from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = {
            "database_filename": "uploadmonitor.sqlite3",
            "log_each_upload": True,
            "store_event_rows": True,
        }

        self.metasettings = {
            "database_filename": {
                "description": "SQLite database file name, stored inside the plugin folder:",
                "type": "string",
            },
            "log_each_upload": {
                "description": "Write a Nicotine+ log entry for every finished upload",
                "type": "bool",
            },
            "store_event_rows": {
                "description": "Store one detail row per finished upload in table upload_events",
                "type": "bool",
            },
        }

        self.db_path = None
        self.conn = None

    def init(self):
        database_filename = (self.settings.get("database_filename") or "uploadmonitor.sqlite3").strip()
        if not database_filename:
            database_filename = "uploadmonitor.sqlite3"

        self.db_path = os.path.join(self.path, database_filename)
        self._open_database()
        self.log("SQLite database ready: %s", self.db_path)

    def disable(self):
        self._close_database()

    def shutdown_notification(self):
        self._close_database()

    def upload_finished_notification(self, user, virtual_path, real_path):
        if not user:
            return

        size_bytes = self._get_file_size(real_path)
        now = datetime.now()
        upload_date = now.date().isoformat()
        timestamp = now.isoformat(timespec="seconds")

        try:
            conn = self._get_connection()
            with conn:
                if self.settings.get("store_event_rows", True):
                    conn.execute(
                        """
                        INSERT INTO upload_events (
                            event_ts,
                            upload_date,
                            username,
                            virtual_path,
                            real_path,
                            bytes_uploaded
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            timestamp,
                            upload_date,
                            user,
                            virtual_path or "",
                            real_path or "",
                            size_bytes,
                        ),
                    )

                conn.execute(
                    """
                    INSERT INTO daily_uploads (
                        username,
                        upload_date,
                        bytes_uploaded,
                        files_uploaded,
                        updated_at
                    ) VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(username, upload_date) DO UPDATE SET
                        bytes_uploaded = daily_uploads.bytes_uploaded + excluded.bytes_uploaded,
                        files_uploaded = daily_uploads.files_uploaded + 1,
                        updated_at = excluded.updated_at
                    """,
                    (user, upload_date, size_bytes, timestamp),
                )

                conn.execute(
                    """
                    INSERT INTO user_totals (
                        username,
                        total_bytes_uploaded,
                        total_files_uploaded,
                        first_seen_date,
                        updated_at
                    ) VALUES (?, ?, 1, ?, ?)
                    ON CONFLICT(username) DO UPDATE SET
                        total_bytes_uploaded = user_totals.total_bytes_uploaded + excluded.total_bytes_uploaded,
                        total_files_uploaded = user_totals.total_files_uploaded + 1,
                        updated_at = excluded.updated_at
                    """,
                    (user, size_bytes, upload_date, timestamp),
                )
                
            if self.settings.get("log_each_upload", True):
                self.log(
                    "Upload finished for %s: %s (%d bytes)",
                    (user, virtual_path or real_path or "<unknown file>", size_bytes),
                )

        except Exception as error:
            self.log("Failed to write upload data for %s: %s", (user, error))

    def _get_file_size(self, real_path):
        if not real_path:
            return 0

        try:
            return int(os.path.getsize(real_path))
        except OSError as error:
            self.log("Could not determine file size for %s: %s", (real_path, error))
            return 0

    def _get_connection(self):
        if self.conn is None:
            self._open_database()
        return self.conn

    def _open_database(self):
        os.makedirs(self.path, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS upload_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_ts TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                username TEXT NOT NULL,
                virtual_path TEXT,
                real_path TEXT,
                bytes_uploaded INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS daily_uploads (
                username TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                bytes_uploaded INTEGER NOT NULL DEFAULT 0,
                files_uploaded INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (username, upload_date)
            );

            CREATE TABLE IF NOT EXISTS user_totals (
                username TEXT PRIMARY KEY,
                total_bytes_uploaded INTEGER NOT NULL DEFAULT 0,
                total_files_uploaded INTEGER NOT NULL DEFAULT 0,
                first_seen_date TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_upload_events_user_date
                ON upload_events (username, upload_date);

            CREATE INDEX IF NOT EXISTS idx_daily_uploads_date
                ON daily_uploads (upload_date);
            """
        )
        self.conn.commit()

    def _close_database(self):
        if self.conn is None:
            return

        try:
            self.conn.close()
        finally:
            self.conn = None
