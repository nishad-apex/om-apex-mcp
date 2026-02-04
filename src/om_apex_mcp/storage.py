"""Storage backend abstraction for Om Apex MCP Server.

Provides a unified interface for file I/O that works with both
local filesystem (Google Drive Desktop sync) and Google Drive API (remote).

Error Handling:
- All file operations are wrapped in try/except
- Errors are logged with full context
- Methods return sensible defaults (empty dict/list, None) on error
- The server continues running even if storage operations fail
"""

import json
import logging
import os
import platform
import sys
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger("om-apex-mcp")


class StorageBackend(ABC):
    """Abstract storage backend for reading/writing data files."""

    @abstractmethod
    def load_json(self, filename: str) -> dict:
        """Load a JSON file from the mcp-data directory."""
        ...

    @abstractmethod
    def save_json(self, filename: str, data: dict) -> None:
        """Save data to a JSON file in the mcp-data directory."""
        ...

    @abstractmethod
    def read_text(self, path: str) -> Optional[str]:
        """Read a text file by relative path from shared drive root. Returns None if not found."""
        ...

    @abstractmethod
    def write_text(self, path: str, content: str) -> None:
        """Write a text file by relative path from shared drive root."""
        ...

    @abstractmethod
    def append_text(self, path: str, content: str) -> None:
        """Append to a text file by relative path from shared drive root."""
        ...

    @abstractmethod
    def list_files(self, directory: str, pattern: str = "*.md") -> list[str]:
        """List files in a directory matching a glob pattern. Returns relative paths."""
        ...

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if a file exists at the given relative path from shared drive root."""
        ...


class LocalStorage(StorageBackend):
    """Local filesystem storage — reads/writes via Google Drive Desktop sync.

    All operations are wrapped in error handling to prevent crashes.
    """

    def __init__(self, data_dir: Optional[Path] = None, shared_drive_root: Optional[Path] = None):
        """Initialize LocalStorage with paths to data directory and shared drive.

        Args:
            data_dir: Path to mcp-data directory. Auto-detected if None.
            shared_drive_root: Path to shared drive root. Defaults to data_dir parent.

        Raises:
            RuntimeError: If the data directory cannot be determined or accessed.
        """
        try:
            if data_dir is None:
                data_dir = self._get_default_data_dir()
            self.data_dir = Path(data_dir).expanduser()
            self.shared_drive_root = shared_drive_root or self.data_dir.parent

            # Validate paths exist
            if not self.data_dir.exists():
                logger.warning(f"Data directory does not exist: {self.data_dir}")
                logger.warning("Creating data directory...")
                try:
                    self.data_dir.mkdir(parents=True, exist_ok=True)
                except Exception as mkdir_err:
                    logger.error(f"Failed to create data directory: {mkdir_err}")

            if not self.shared_drive_root.exists():
                logger.warning(f"Shared drive root does not exist: {self.shared_drive_root}")
                logger.warning("Google Drive may not be synced or mounted")

            logger.info(f"LocalStorage: data_dir={self.data_dir}, shared_drive_root={self.shared_drive_root}")

        except Exception as e:
            logger.error(f"LocalStorage initialization error: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"Failed to initialize LocalStorage: {e}") from e

    @staticmethod
    def _get_default_data_dir() -> Path:
        """Determine the default data directory based on platform.

        Returns:
            Path to the mcp-data directory.
        """
        try:
            system = platform.system()
            logger.info(f"Detecting data directory for platform: {system}")

            if system == "Darwin":
                path = Path.home() / "Library/CloudStorage/GoogleDrive-nishad@omapex.com/Shared drives/om-apex/mcp-data"
            elif system == "Windows":
                path = Path("H:/Shared drives/om-apex/mcp-data")
            else:
                path = Path(__file__).parent.parent.parent / "data" / "context"

            logger.info(f"Default data directory: {path}")
            return path

        except Exception as e:
            logger.error(f"Error determining default data dir: {e}")
            # Fallback to a local directory
            fallback = Path.home() / ".om-apex-mcp/data"
            logger.warning(f"Using fallback data directory: {fallback}")
            return fallback

    def load_json(self, filename: str) -> dict:
        """Load a JSON file from the data directory.

        Returns empty dict on any error (file not found, parse error, etc.)
        """
        filepath = self.data_dir / filename
        try:
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.debug(f"JSON file not found (returning empty dict): {filepath}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            logger.error(f"File may be corrupted. Consider restoring from backup.")
            return {}
        except PermissionError as e:
            logger.error(f"Permission denied reading {filepath}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {}

    def save_json(self, filename: str, data: dict) -> None:
        """Save data to a JSON file in the data directory.

        Raises exception on error to allow caller to handle it.
        """
        filepath = self.data_dir / filename
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then rename for atomicity
            temp_path = filepath.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(filepath)
            logger.debug(f"Saved JSON to {filepath}")
        except PermissionError as e:
            logger.error(f"Permission denied writing to {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving JSON to {filepath}: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise

    def read_text(self, path: str) -> Optional[str]:
        """Read a text file by relative path from shared drive root.

        Returns None if file not found or on error.
        """
        filepath = self.shared_drive_root / path
        try:
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                logger.debug(f"Text file not found: {filepath}")
                return None
        except PermissionError as e:
            logger.error(f"Permission denied reading {filepath}: {e}")
            return None
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {filepath}: {e}")
            # Try with a different encoding
            try:
                with open(filepath, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception:
                return None
        except Exception as e:
            logger.error(f"Error reading text from {filepath}: {e}")
            return None

    def write_text(self, path: str, content: str) -> None:
        """Write a text file by relative path from shared drive root."""
        filepath = self.shared_drive_root / path
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug(f"Wrote text to {filepath}")
        except PermissionError as e:
            logger.error(f"Permission denied writing to {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error writing text to {filepath}: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise

    def append_text(self, path: str, content: str) -> None:
        """Append to a text file by relative path from shared drive root."""
        filepath = self.shared_drive_root / path
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content)
            logger.debug(f"Appended text to {filepath}")
        except PermissionError as e:
            logger.error(f"Permission denied appending to {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error appending text to {filepath}: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise

    def list_files(self, directory: str, pattern: str = "*.md") -> list[str]:
        """List files in a directory matching a glob pattern.

        Returns empty list on error.
        """
        dir_path = self.shared_drive_root / directory
        try:
            if not dir_path.exists():
                logger.debug(f"Directory not found: {dir_path}")
                return []
            files = sorted(
                [str(f.relative_to(self.shared_drive_root)) for f in dir_path.glob(pattern)],
                reverse=True,
            )
            logger.debug(f"Found {len(files)} files matching {pattern} in {directory}")
            return files
        except PermissionError as e:
            logger.error(f"Permission denied listing {dir_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing files in {dir_path}: {e}")
            return []

    def file_exists(self, path: str) -> bool:
        """Check if a file exists at the given relative path."""
        try:
            return (self.shared_drive_root / path).exists()
        except Exception as e:
            logger.error(f"Error checking file existence for {path}: {e}")
            return False


class GoogleDriveStorage(StorageBackend):
    """Google Drive API storage for remote access via service account."""

    def __init__(self):
        import json as _json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Support key as file path OR inline JSON (for Render/containers)
        creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

        if creds_json:
            info = _json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
        elif creds_path:
            creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
        else:
            raise ValueError("Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE")
        self.service = build("drive", "v3", credentials=creds)

        # Shared Drive ID — set via env var or auto-discover
        self.shared_drive_id = os.environ.get("GOOGLE_SHARED_DRIVE_ID", "")
        if not self.shared_drive_id:
            self.shared_drive_id = self._find_shared_drive("om-apex")

        # Cache: relative path -> Drive file ID
        self._file_id_cache: dict[str, str] = {}
        # Cache: folder relative path -> Drive folder ID
        self._folder_id_cache: dict[str, str] = {}

        logger.info(f"GoogleDriveStorage: shared_drive_id={self.shared_drive_id}")

    def _find_shared_drive(self, name: str) -> str:
        """Find a shared drive by name."""
        response = self.service.drives().list(
            q=f"name = '{name}'",
            fields="drives(id, name)",
        ).execute()
        drives = response.get("drives", [])
        if not drives:
            raise ValueError(f"Shared Drive '{name}' not found")
        return drives[0]["id"]

    def _resolve_folder_id(self, folder_path: str) -> str:
        """Resolve a folder path to a Drive folder ID, walking the path."""
        if not folder_path or folder_path == ".":
            return self.shared_drive_id

        if folder_path in self._folder_id_cache:
            return self._folder_id_cache[folder_path]

        parts = folder_path.strip("/").split("/")
        parent_id = self.shared_drive_id

        for part in parts:
            current_path = "/".join(parts[:parts.index(part) + 1])
            if current_path in self._folder_id_cache:
                parent_id = self._folder_id_cache[current_path]
                continue

            response = self.service.files().list(
                q=f"name = '{part}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=self.shared_drive_id,
            ).execute()
            files = response.get("files", [])
            if not files:
                raise FileNotFoundError(f"Folder not found: {folder_path} (missing: {part})")
            parent_id = files[0]["id"]
            self._folder_id_cache[current_path] = parent_id

        return parent_id

    def _resolve_file_id(self, path: str) -> Optional[str]:
        """Resolve a relative file path to a Drive file ID."""
        if path in self._file_id_cache:
            return self._file_id_cache[path]

        parts = path.strip("/").rsplit("/", 1)
        if len(parts) == 2:
            folder_path, filename = parts
        else:
            folder_path, filename = "", parts[0]

        try:
            parent_id = self._resolve_folder_id(folder_path)
        except FileNotFoundError:
            return None

        response = self.service.files().list(
            q=f"name = '{filename}' and '{parent_id}' in parents and trashed = false",
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="drive",
            driveId=self.shared_drive_id,
        ).execute()
        files = response.get("files", [])
        if not files:
            return None

        file_id = files[0]["id"]
        self._file_id_cache[path] = file_id
        return file_id

    def _download_content(self, file_id: str) -> str:
        """Download file content by ID."""
        from googleapiclient.http import MediaIoBaseDownload
        import io

        request = self.service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True,
        )
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue().decode("utf-8")

    def _upload_content(self, path: str, content: str, mime_type: str = "application/json") -> str:
        """Upload or update file content. Returns file ID."""
        from googleapiclient.http import MediaInMemoryUpload

        file_id = self._resolve_file_id(path)
        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype=mime_type)

        if file_id:
            # Update existing file
            self.service.files().update(
                fileId=file_id,
                media_body=media,
                supportsAllDrives=True,
            ).execute()
            return file_id
        else:
            # Create new file
            parts = path.strip("/").rsplit("/", 1)
            if len(parts) == 2:
                folder_path, filename = parts
            else:
                folder_path, filename = "", parts[0]

            parent_id = self._resolve_folder_id(folder_path)
            file_metadata = {
                "name": filename,
                "parents": [parent_id],
            }
            result = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()
            new_id = result["id"]
            self._file_id_cache[path] = new_id
            return new_id

    def load_json(self, filename: str) -> dict:
        path = f"mcp-data/{filename}"
        file_id = self._resolve_file_id(path)
        if not file_id:
            return {}
        content = self._download_content(file_id)
        return json.loads(content)

    def save_json(self, filename: str, data: dict) -> None:
        path = f"mcp-data/{filename}"
        content = json.dumps(data, indent=2)
        self._upload_content(path, content, mime_type="application/json")

    def read_text(self, path: str) -> Optional[str]:
        file_id = self._resolve_file_id(path)
        if not file_id:
            return None
        return self._download_content(file_id)

    def write_text(self, path: str, content: str) -> None:
        self._upload_content(path, content, mime_type="text/plain")

    def append_text(self, path: str, content: str) -> None:
        existing = self.read_text(path)
        if existing:
            content = existing + content
        self._upload_content(path, content, mime_type="text/plain")

    def list_files(self, directory: str, pattern: str = "*.md") -> list[str]:
        try:
            folder_id = self._resolve_folder_id(directory)
        except FileNotFoundError:
            return []

        # Convert glob pattern to a simple suffix match
        # Supports "*.md" style patterns
        suffix = ""
        if pattern.startswith("*"):
            suffix = pattern[1:]

        results = []
        page_token = None
        while True:
            q = f"'{folder_id}' in parents and trashed = false"
            if suffix:
                q += f" and name contains '{suffix}'"

            response = self.service.files().list(
                q=q,
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=self.shared_drive_id,
                pageToken=page_token,
            ).execute()

            for f in response.get("files", []):
                rel_path = f"{directory}/{f['name']}"
                self._file_id_cache[rel_path] = f["id"]
                if not suffix or f["name"].endswith(suffix):
                    results.append(rel_path)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return sorted(results, reverse=True)

    def file_exists(self, path: str) -> bool:
        return self._resolve_file_id(path) is not None
