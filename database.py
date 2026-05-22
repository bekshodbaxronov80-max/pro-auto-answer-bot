"""
SQLite ma'lumotlar bazasi.
Hosting uchun mos - PostgreSQL kerak emas!
"""

import sqlite3
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.Error as e:
            print(f"Bazaga ulanishda xatolik: {e}")
            raise

    def _create_tables(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en',
                bot_status TEXT DEFAULT 'active',
                business_connection_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                trigger_text TEXT NOT NULL,
                reply_text TEXT NOT NULL,
                reply_type TEXT DEFAULT 'exact',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_settings (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT,
                provider TEXT DEFAULT 'openai',
                model_name TEXT DEFAULT 'gpt-3.5-turbo',
                max_tokens INTEGER DEFAULT 1000,
                temperature REAL DEFAULT 0.7,
                system_prompt TEXT,
                is_active INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, language: str = "en") -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, language, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """, (user_id, language))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_language(self, user_id: int, language: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, language, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET 
                    language = ?, updated_at = CURRENT_TIMESTAMP
            """, (user_id, language, language))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def update_bot_status(self, user_id: int, status: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET bot_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (status, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def save_business_connection(self, user_id: int, connection_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET business_connection_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (connection_id, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def remove_business_connection(self, user_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET business_connection_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def add_auto_reply(self, user_id: int, trigger_text: str, reply_text: str,
                       reply_type: str = "exact") -> Optional[int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO auto_replies (user_id, trigger_text, reply_text, reply_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, trigger_text.strip().lower(), reply_text, reply_type))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Xatolik: {e}")
            return None
        finally:
            conn.close()

    def get_auto_replies(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM auto_replies WHERE user_id = ? AND is_active = 1
            ORDER BY id DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def find_matching_reply(self, user_id: int, message_text: str) -> Optional[str]:
        if not message_text:
            return None
        message_lower = message_text.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trigger_text, reply_text FROM auto_replies
            WHERE user_id = ? AND is_active = 1
            ORDER BY id DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            trigger = row["trigger_text"]
            if trigger in message_lower or message_lower == trigger:
                return row["reply_text"]
        return None

    def delete_auto_reply(self, user_id: int, reply_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM auto_replies WHERE id = ? AND user_id = ?
            """, (reply_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def save_ai_settings(self, user_id: int, **kwargs) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ai_settings (user_id, api_key, provider, model_name,
                                        max_tokens, temperature, system_prompt, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    api_key = COALESCE(?, api_key),
                    provider = COALESCE(?, provider),
                    model_name = COALESCE(?, model_name),
                    max_tokens = COALESCE(?, max_tokens),
                    temperature = COALESCE(?, temperature),
                    system_prompt = COALESCE(?, system_prompt),
                    is_active = COALESCE(?, is_active)
            """, (
                user_id, kwargs.get("api_key"), kwargs.get("provider", "openai"),
                kwargs.get("model_name", "gpt-3.5-turbo"), kwargs.get("max_tokens", 1000),
                kwargs.get("temperature", 0.7), kwargs.get("system_prompt"),
                kwargs.get("is_active", 0),
                kwargs.get("api_key"), kwargs.get("provider", "openai"),
                kwargs.get("model_name", "gpt-3.5-turbo"), kwargs.get("max_tokens", 1000),
                kwargs.get("temperature", 0.7), kwargs.get("system_prompt"),
                kwargs.get("is_active", 0),
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def get_ai_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ai_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_ai_provider(self, user_id: int, provider: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ai_settings (user_id, provider)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET provider = ?
            """, (user_id, provider, provider))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def delete_api_key(self, user_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE ai_settings SET api_key = NULL, is_active = 0 WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Xatolik: {e}")
            return False
        finally:
            conn.close()

    def get_all_active_users(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE bot_status = 'active'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_by_business_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE business_connection_id = ?", (connection_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


db = Database()