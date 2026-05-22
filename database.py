"""
Oracle Cloud PostgreSQL uchun database.py
"""

import os
import psycopg2
import psycopg2.extras
from typing import Optional, List, Dict, Any

# PostgreSQL sozlamalari
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "bot_database")
DB_USER = os.environ.get("DB_USER", "bot_user")
DB_PASS = os.environ.get("DB_PASS", "KuchliParol123!")
DB_PORT = os.environ.get("DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class Database:
    def __init__(self):
        self.db_url = DATABASE_URL
        self._create_tables()

    def _get_connection(self):
        conn = psycopg2.connect(self.db_url)
        conn.autocommit = True
        return conn

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                language TEXT DEFAULT 'en',
                bot_status TEXT DEFAULT 'active',
                business_connection_id TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_replies (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                trigger_text TEXT NOT NULL,
                reply_text TEXT NOT NULL,
                reply_type TEXT DEFAULT 'exact',
                is_active SMALLINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_settings (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                api_key TEXT,
                provider TEXT DEFAULT 'openai',
                model_name TEXT DEFAULT 'gpt-3.5-turbo',
                max_tokens INTEGER DEFAULT 1000,
                temperature REAL DEFAULT 0.7,
                system_prompt TEXT,
                is_active SMALLINT DEFAULT 0
            )
        """)
        
        # Indexlar (tez qidirish uchun)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_business 
            ON users(business_connection_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_replies_user 
            ON auto_replies(user_id)
        """)
        
        conn.commit()
        conn.close()

    def add_user(self, user_id: int, language: str = "en") -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, language, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT(user_id) DO UPDATE SET updated_at = NOW()
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def update_language(self, user_id: int, language: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, language, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT(user_id) DO UPDATE SET 
                    language = %s, updated_at = NOW()
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
                UPDATE users SET bot_status = %s, updated_at = NOW()
                WHERE user_id = %s
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
                UPDATE users SET business_connection_id = %s, updated_at = NOW()
                WHERE user_id = %s
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
                UPDATE users SET business_connection_id = NULL, updated_at = NOW()
                WHERE user_id = %s
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
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (user_id, trigger_text.strip().lower(), reply_text, reply_type))
            result = cursor.fetchone()
            conn.commit()
            return result[0]
        except Exception as e:
            print(f"Xatolik: {e}")
            return None
        finally:
            conn.close()

    def get_auto_replies(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM auto_replies
            WHERE user_id = %s AND is_active = 1
            ORDER BY id DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def find_matching_reply(self, user_id: int, message_text: str) -> Optional[str]:
        if not message_text:
            return None
        message_lower = message_text.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trigger_text, reply_text FROM auto_replies
            WHERE user_id = %s AND is_active = 1
            ORDER BY id DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            trigger, reply = row[0], row[1]
            if trigger in message_lower or message_lower == trigger:
                return reply
        return None

    def delete_auto_reply(self, user_id: int, reply_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM auto_replies WHERE id = %s AND user_id = %s
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    api_key = COALESCE(%s, ai_settings.api_key),
                    provider = COALESCE(%s, ai_settings.provider),
                    model_name = COALESCE(%s, ai_settings.model_name),
                    max_tokens = COALESCE(%s, ai_settings.max_tokens),
                    temperature = COALESCE(%s, ai_settings.temperature),
                    system_prompt = COALESCE(%s, ai_settings.system_prompt),
                    is_active = COALESCE(%s, ai_settings.is_active)
            """, (
                user_id,
                kwargs.get("api_key"),
                kwargs.get("provider", "openai"),
                kwargs.get("model_name", "gpt-3.5-turbo"),
                kwargs.get("max_tokens", 1000),
                kwargs.get("temperature", 0.7),
                kwargs.get("system_prompt"),
                kwargs.get("is_active", 0),
                kwargs.get("api_key"),
                kwargs.get("provider", "openai"),
                kwargs.get("model_name", "gpt-3.5-turbo"),
                kwargs.get("max_tokens", 1000),
                kwargs.get("temperature", 0.7),
                kwargs.get("system_prompt"),
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM ai_settings WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def save_ai_provider(self, user_id: int, provider: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ai_settings (user_id, provider)
                VALUES (%s, %s)
                ON CONFLICT(user_id) DO UPDATE SET provider = %s
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
                UPDATE ai_settings SET api_key = NULL, is_active = 0 WHERE user_id = %s
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE bot_status = 'active'")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_user_by_business_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT * FROM users WHERE business_connection_id = %s",
            (connection_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row


db = Database()