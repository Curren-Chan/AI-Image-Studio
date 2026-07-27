# -*- coding: utf-8 -*-
import os
import json
import logging
import threading
from services.base import BaseService

class SettingsService(BaseService):
    def __init__(self, db_service=None, project_root: str | None = None):
        super().__init__(db_service)
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._settings_lock = threading.RLock()
        self.settings_json_path = os.path.join(project_root, "settings.json")
        self.env_path = os.path.join(project_root, ".env")
        
        # Load API keys from env
        from dotenv import load_dotenv
        load_dotenv(self.env_path)
        self.api_key = os.getenv("OPENAI_API_KEY") or ""
        self.fal_key = os.getenv("FAL_KEY") or ""
        self.gemini_key = os.getenv("GEMINI_API_KEY") or ""
        self.xai_key = os.getenv("XAI_API_KEY") or ""
        self.hotapi_key = os.getenv("HOTAPI_KEY") or ""
        
        # Load defaults
        self.defaults = {
            "balance_openai": "10.00",
            "balance_fal": "10.00",
            "balance_grok": "10.00",
            "balance_hotapi": "10.00",
            "theme": "Dark",
            "translation_provider": "openai",
            "enabled_models": "openai-gpt-image-2,fal-flux-2-pro,fal-flux-1-dev,fal-grok-imagine-standard,fal-grok-imagine-quality,xai-grok-imagine-quality,xai-grok-imagine-standard"
        }
        self.ensure_settings_json()
        
        # Migration: Map old balance key to balance_openai if exists
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'balance';")
            row = cursor.fetchone()
            if row:
                old_val = row[0]
                cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('balance_openai', ?);", (old_val,))
                cursor.execute("DELETE FROM settings WHERE key = 'balance';")
                conn.commit()
        except Exception as exc:
            logging.warning("Could not migrate legacy balance setting: %s", exc)
        finally:
            if conn is not None:
                conn.close()

        enabled_models = str(self.get_setting("enabled_models", "") or "")
        if "fal-flux-2-dev" in enabled_models:
            migrated = enabled_models.replace("fal-flux-2-dev", "fal-flux-1-dev")
            self.save_setting("enabled_models", migrated)
        
    def ensure_settings_json(self):
        """Pre-populates settings.json if not present."""
        if not os.path.exists(self.settings_json_path):
            try:
                self._write_json_atomic(self.defaults)
            except Exception as e:
                logging.error(f"Failed to create defaults settings.json: {e}")

    def get_setting(self, key: str, default_val=None):
        with self._settings_lock:
            conn = None
            try:
                conn = self.get_connection()
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = ?;", (key,)
                ).fetchone()
                if row:
                    return row[0]
            except Exception as exc:
                logging.warning("Failed to read setting %s from DB: %s", key, exc)
            finally:
                if conn is not None:
                    conn.close()

            try:
                data = self._read_json()
                if key in data:
                    return data[key]
            except (OSError, ValueError, TypeError) as exc:
                logging.warning("Failed to read settings.json: %s", exc)

            if default_val is not None:
                return default_val
            return self.defaults.get(key)

    def save_setting(self, key: str, value: str) -> bool:
        with self._settings_lock:
            db_saved = self._save_db_setting(key, value)
            try:
                data = self._read_json()
                data[key] = value
                self._write_json_atomic(data)
                json_saved = True
            except Exception as exc:
                logging.error("Failed to write settings.json: %s", exc)
                json_saved = False
            # Either durable store is sufficient for recovery; both are kept
            # in sync during normal operation.
            return db_saved or json_saved

    def deduct_balance(self, key: str, amount: float) -> float:
        """Atomically deduct a provider charge within this application process."""
        with self._settings_lock:
            try:
                current = float(self.get_setting(key, "10.00"))
            except (TypeError, ValueError):
                current = 10.0
            new_balance = max(0.0, current - max(0.0, float(amount)))
            if not self.save_setting(key, f"{new_balance:.5f}"):
                raise OSError(f"Could not persist updated balance for {key}")
            return new_balance

    def _save_db_setting(self, key: str, value: str) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);",
                (key, str(value)),
            )
            conn.commit()
            return True
        except Exception as exc:
            logging.error("Failed to save setting %s in DB: %s", key, exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    def _read_json(self) -> dict:
        if not os.path.exists(self.settings_json_path):
            return {}
        with open(self.settings_json_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise TypeError("settings.json root must be an object")
        return data

    def _write_json_atomic(self, data: dict):
        temp_path = (
            f"{self.settings_json_path}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.settings_json_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_api_key(self) -> str:
        return self.api_key

    def update_api_key(self, api_key: str):
        self.api_key = api_key
        self._update_env_var("OPENAI_API_KEY", api_key)

    def get_fal_key(self) -> str:
        return self.fal_key

    def update_fal_key(self, fal_key: str):
        self.fal_key = fal_key
        self._update_env_var("FAL_KEY", fal_key)

    def get_gemini_key(self) -> str:
        return self.gemini_key

    def update_gemini_key(self, gemini_key: str):
        self.gemini_key = gemini_key
        self._update_env_var("GEMINI_API_KEY", gemini_key)

    def get_xai_key(self) -> str:
        return self.xai_key

    def update_xai_key(self, xai_key: str):
        self.xai_key = xai_key
        self._update_env_var("XAI_API_KEY", xai_key)

    def get_hotapi_key(self) -> str:
        return self.hotapi_key

    def update_hotapi_key(self, hotapi_key: str):
        self.hotapi_key = hotapi_key
        self._update_env_var("HOTAPI_KEY", hotapi_key)

    def _update_env_var(self, name: str, value: str):
        value = str(value or "").replace("\r", "").replace("\n", "")
        with self._settings_lock:
            if value:
                os.environ[name] = value
            else:
                os.environ.pop(name, None)
            temp_path = None
            try:
                lines = []
                if os.path.exists(self.env_path):
                    with open(self.env_path, "r", encoding="utf-8") as handle:
                        lines = handle.readlines()
                new_lines = []
                found = False
                for line in lines:
                    if line.strip().startswith(f"{name}="):
                        new_lines.append(f"{name}={value}\n")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"{name}={value}\n")
                temp_path = (
                    f"{self.env_path}.{os.getpid()}.{threading.get_ident()}.tmp"
                )
                with open(temp_path, "w", encoding="utf-8") as handle:
                    handle.writelines(new_lines)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, self.env_path)
            except Exception as exc:
                logging.error("Failed to write %s to .env: %s", name, exc)
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
