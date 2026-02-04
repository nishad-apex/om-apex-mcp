"""Shared utilities for all tool modules.

Error Handling:
- All functions are wrapped to prevent crashes
- Sensible defaults are returned on error
- Errors are logged with full context
"""

import logging
import traceback
from typing import Optional

logger = logging.getLogger("om-apex-mcp")

# Global storage backend — initialized by server startup
_backend = None  # Type: Optional[StorageBackend]

# Relative path for daily progress within shared drive
DAILY_PROGRESS_REL = "business-plan/06 HR and Admin/Daily Progress"

# Flag to prefer Supabase for tasks/decisions when available
_use_supabase = True


def init_storage(backend, use_supabase: bool = True) -> None:
    """Initialize the global storage backend. Called once at server startup.

    Args:
        backend: Storage backend for file operations (daily progress, documents, etc.)
        use_supabase: Whether to use Supabase for tasks/decisions when available.

    Note: Does not raise exceptions - logs errors and continues.
    """
    global _backend, _use_supabase

    try:
        _backend = backend
        _use_supabase = use_supabase
        logger.info(f"Storage backend initialized: {type(backend).__name__}")

        # Check Supabase availability (import here to avoid circular import)
        if use_supabase:
            try:
                from ..supabase_client import is_supabase_available
                if is_supabase_available():
                    logger.info("Supabase available - using for tasks and decisions")
                else:
                    logger.info("Supabase not available - using file storage for tasks/decisions")
            except ImportError as e:
                logger.warning(f"Could not import supabase_client: {e}")
            except Exception as e:
                logger.warning(f"Error checking Supabase availability: {e}")
    except Exception as e:
        logger.error(f"Error in init_storage: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")


def get_backend():
    """Get the current storage backend, lazily initializing if needed.

    Returns:
        StorageBackend instance. Creates LocalStorage if not initialized.
    """
    global _backend

    if _backend is None:
        try:
            # Import here to avoid circular import at module load time
            from ..storage import LocalStorage
            _backend = LocalStorage()
            logger.info("Storage backend auto-initialized to LocalStorage")
        except Exception as e:
            logger.error(f"Failed to auto-initialize LocalStorage: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"Cannot initialize storage backend: {e}") from e

    return _backend


def load_json(filename: str) -> dict:
    """Load a JSON file from the data directory."""
    return get_backend().load_json(filename)


def save_json(filename: str, data: dict) -> None:
    """Save data to a JSON file in the data directory."""
    get_backend().save_json(filename, data)


def get_claude_instructions_data() -> dict:
    """Return behavioral instructions for Claude across all platforms."""
    return {
        "session_start": {
            "description": "How to behave when starting a new conversation",
            "steps": [
                "1. Call get_full_context automatically at conversation start",
                "2. Output ONLY a brief 2-3 line greeting (see greeting_format below)",
                "3. Do NOT dump full context details to the user - you have the data internally",
                "4. Wait for user's first request"
            ],
            "greeting_format": {
                "template": "Full context loaded.\n\n**Quick Summary:** X pending tasks (Y high priority)\n\nHow can I help you today?",
                "rules": [
                    "Replace X with total pending task count",
                    "Replace Y with high priority task count",
                    "Do NOT list tasks, decisions, tech stack, or other details",
                    "Do NOT explain what context was loaded",
                    "Keep it to exactly 3 lines as shown in template"
                ]
            }
        },
        "session_end": {
            "description": "How to behave when user says 'end session', 'wrap up', 'save our work', or similar",
            "steps": [
                "1. Review the entire conversation for: decisions made, tasks completed, new tasks identified",
                "2. Summarize findings to user: 'I found X decisions, Y new tasks, Z completed tasks'",
                "3. Get user confirmation before saving",
                "4. Call add_decision for each decision (with area, decision, rationale, company)",
                "5. Call add_task for each new task",
                "6. Call complete_task for each completed task",
                "7. Call add_daily_progress with structured data",
                "8. Confirm everything was saved successfully"
            ],
            "add_daily_progress_format": {
                "person": "Nishad or Sumedha (whoever is running the session)",
                "interface": "code, code-app, cowork, or chat (lowercase)",
                "title": "Brief title of main work done",
                "completed": ["List of items completed"],
                "decisions": ["TECH-XXX: Description"],
                "tasks_completed": ["TASK-XXX: Description"],
                "tasks_created": ["TASK-XXX: Description"],
                "files_modified": ["path/to/file - description"],
                "notes": ["Important context for future reference"]
            }
        },
        "general_behavior": {
            "tone": "Professional, concise, helpful",
            "response_style": [
                "Keep responses focused and actionable",
                "Use markdown formatting for readability",
                "When listing tasks, show ID and description",
                "Don't over-explain - users are familiar with their business"
            ],
            "proactive_actions": [
                "Offer to save decisions when significant choices are made",
                "Suggest creating tasks for follow-up items",
                "Remind about session end protocol if conversation seems to be wrapping up"
            ]
        },
        "owners": {
            "Nishad": "Primary technical owner, supply chain expert, handles most Claude sessions",
            "Sumedha": "Co-owner, handles content, website updates, and some technical tasks"
        }
    }
