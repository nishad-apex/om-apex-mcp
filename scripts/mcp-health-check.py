#!/usr/bin/env python3
"""
MCP Health Check - Detailed Diagnostics

Standalone diagnostic tool for the Om Apex MCP Server.
Checks all dependencies, configurations, and connectivity.

Author: Claude (via TASK-163)
"""

import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def pass_msg(msg: str) -> None:
    print(f"{GREEN}[PASS]{RESET} {msg}")


def fail_msg(msg: str, fix: str = "") -> None:
    print(f"{RED}[FAIL]{RESET} {msg}")
    if fix:
        print(f"       {YELLOW}Fix:{RESET} {fix}")


def warn_msg(msg: str, note: str = "") -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")
    if note:
        print(f"       {note}")


def info_msg(msg: str) -> None:
    print(f"       {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}--- {title} ---{RESET}")


def check_python_version() -> bool:
    """Check Python version is 3.10+."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major >= 3 and version.minor >= 10:
        pass_msg(f"Python {version_str}")
        return True
    else:
        fail_msg(f"Python {version_str} - requires 3.10+", "Install Python 3.10+")
        return False


def check_mcp_module() -> bool:
    """Check if MCP module can be imported."""
    try:
        import mcp
        pass_msg(f"MCP module importable (version {getattr(mcp, '__version__', 'unknown')})")
        return True
    except ImportError as e:
        fail_msg(f"MCP module not importable: {e}", "pip install mcp")
        return False


def check_om_apex_module() -> bool:
    """Check if om_apex_mcp module can be imported."""
    try:
        import om_apex_mcp
        pass_msg("om_apex_mcp module importable")
        return True
    except ImportError as e:
        fail_msg(f"om_apex_mcp module not importable: {e}", "pip install -e . (from mcp-server directory)")
        return False


def check_required_packages() -> bool:
    """Check that all required packages are installed."""
    required = [
        ("mcp", "mcp"),
        ("pydantic", "pydantic"),
        ("python-dotenv", "dotenv"),
        ("supabase", "supabase"),
        ("starlette", "starlette"),
        ("uvicorn", "uvicorn"),
    ]

    all_ok = True
    for pkg_name, import_name in required:
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            pass_msg(f"Package '{pkg_name}' installed")
        else:
            fail_msg(f"Package '{pkg_name}' not installed", f"pip install {pkg_name}")
            all_ok = False

    return all_ok


def check_env_config() -> bool:
    """Check environment configuration files exist."""
    # Determine config path based on platform
    if platform.system() == "Darwin":
        config_dir = Path.home() / "om-apex/config"
    elif platform.system() == "Windows":
        config_dir = Path("C:/Users/14042/om-apex/config")
    else:
        config_dir = Path.home() / "om-apex/config"

    if not config_dir.exists():
        warn_msg(f"Config directory not found: {config_dir}", "This is OK for demo mode")
        return True  # Not a hard failure

    pass_msg(f"Config directory exists: {config_dir}")

    # Check for Supabase config
    supabase_config = config_dir / ".env.supabase.omapex-dashboard"
    if supabase_config.exists():
        pass_msg("Supabase config file exists")
    else:
        warn_msg("Supabase config not found", f"Expected: {supabase_config}")

    return True


def check_supabase_connectivity() -> bool:
    """Check Supabase connectivity."""
    try:
        # Import after package check
        from om_apex_mcp.supabase_client import get_supabase_client, is_supabase_available

        if not is_supabase_available():
            warn_msg("Supabase not configured", "Server will use JSON file storage")
            return True  # Not a hard failure - fallback exists

        client = get_supabase_client()
        # Try a simple query
        client.table("tasks").select("id").limit(1).execute()
        pass_msg("Supabase connectivity OK")
        return True
    except ImportError:
        warn_msg("Supabase client not importable", "Install om_apex_mcp first")
        return True
    except Exception as e:
        fail_msg(f"Supabase query failed: {type(e).__name__}: {e}", "Check SUPABASE_URL and credentials")
        return False


def check_storage_paths() -> bool:
    """Check local storage paths exist and are readable."""
    if platform.system() == "Darwin":
        data_dir = Path.home() / "Library/CloudStorage/GoogleDrive-nishad@omapex.com/Shared drives/om-apex/mcp-data"
    elif platform.system() == "Windows":
        data_dir = Path("H:/Shared drives/om-apex/mcp-data")
    else:
        # Fallback for Linux/other
        data_dir = Path(__file__).parent.parent / "data" / "context"

    if data_dir.exists():
        pass_msg(f"Storage path exists: {data_dir}")

        # Check for key files
        company_file = data_dir / "company_structure.json"
        if company_file.exists():
            pass_msg("company_structure.json readable")
        else:
            warn_msg("company_structure.json not found", "Expected in mcp-data directory")

        return True
    else:
        warn_msg(f"Storage path not found: {data_dir}", "Google Drive may not be mounted or synced")
        return True  # Not a hard failure for remote deployments


def check_claude_desktop_config() -> bool:
    """Check Claude Desktop config points to correct path."""
    if platform.system() == "Darwin":
        config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif platform.system() == "Windows":
        config_path = Path(os.environ.get("APPDATA", "")) / "Claude/claude_desktop_config.json"
    else:
        warn_msg("Claude Desktop config check skipped (Linux/other)", "")
        return True

    if not config_path.exists():
        warn_msg(f"Claude Desktop config not found: {config_path}", "Claude Desktop may not be installed")
        return True

    try:
        with open(config_path) as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})
        if "om-apex" not in mcp_servers:
            fail_msg("om-apex MCP server not configured in Claude Desktop",
                    f"Add to {config_path}")
            return False

        om_apex_config = mcp_servers["om-apex"]
        command = om_apex_config.get("command", "")

        # Check if the Python path exists
        if command and not Path(command).exists():
            fail_msg(f"Python path does not exist: {command}",
                    "Update claude_desktop_config.json with correct Python path")
            return False

        pass_msg(f"Claude Desktop config OK")
        info_msg(f"Command: {command}")
        info_msg(f"Args: {om_apex_config.get('args', [])}")
        return True

    except json.JSONDecodeError as e:
        fail_msg(f"Claude Desktop config is invalid JSON: {e}", f"Fix {config_path}")
        return False
    except Exception as e:
        fail_msg(f"Error reading Claude Desktop config: {e}", "")
        return False


def check_http_server() -> bool:
    """Check if HTTP server is running (optional)."""
    import socket

    host = "localhost"
    port = 8000

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()

    if result == 0:
        pass_msg(f"HTTP server running on {host}:{port}")

        # Try to fetch health endpoint
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5) as response:
                data = json.loads(response.read().decode())
                info_msg(f"Health response: {data}")
        except Exception as e:
            warn_msg(f"Could not fetch /health: {e}", "")

        return True
    else:
        info_msg(f"HTTP server not running on {host}:{port} (this is optional)")
        return True  # Not required for stdio transport


def main():
    """Run all health checks."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    all_passed = True
    critical_failed = False

    # Core checks (required)
    section("Core Requirements")
    if not check_python_version():
        critical_failed = True
    if not check_mcp_module():
        critical_failed = True
    if not check_om_apex_module():
        critical_failed = True

    # Package checks
    section("Required Packages")
    if not check_required_packages():
        all_passed = False

    # Configuration checks
    section("Configuration")
    if not check_env_config():
        all_passed = False
    if not check_claude_desktop_config():
        all_passed = False

    # Connectivity checks
    section("Connectivity")
    if not check_supabase_connectivity():
        all_passed = False
    if not check_storage_paths():
        all_passed = False

    # Optional checks
    section("Optional Services")
    check_http_server()

    # Summary
    section("Summary")
    if critical_failed:
        print(f"\n{RED}{BOLD}CRITICAL FAILURES - MCP server will not start{RESET}")
        print("Fix the issues above before starting Claude Desktop")
        sys.exit(1)
    elif not all_passed:
        print(f"\n{YELLOW}{BOLD}WARNINGS present - MCP server may work in degraded mode{RESET}")
        print("Review warnings above; some features may be unavailable")
        sys.exit(0)
    else:
        print(f"\n{GREEN}{BOLD}All checks passed - MCP server should work correctly{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
