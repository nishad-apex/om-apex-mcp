# Setting Up Om Apex MCP Server on Sumedha's Laptop (Windows 11)

This guide helps set up the Om Apex MCP server on Sumedha's Windows 11 laptop to share context with Nishad's MacBook.

## Prerequisites

- Windows 11
- Python 3.10+ installed (from python.org or Microsoft Store)
- Git installed (from https://git-scm.com/download/win)
- Node.js 18+ installed (from https://nodejs.org)
- Claude Code CLI installed
- Access to the Om Apex Google Drive (sumedha@omapex.com)

## Step 1: Install Claude Code CLI

Open PowerShell as Administrator and run:

```powershell
npm install -g @anthropic-ai/claude-code
```

Verify installation:
```powershell
claude --version
```

## Step 2: Clone the MCP Server Repository

Open PowerShell (regular, not Admin) and run:

```powershell
# Create directory structure
mkdir -p C:\Users\sumedha\om-apex\om-ai
cd C:\Users\sumedha\om-apex\om-ai

# Clone the repository
git clone https://github.com/nishad-apex/om-apex-mcp.git
cd om-apex-mcp
```

## Step 3: Install the MCP Server

```powershell
# Install the package in editable mode
pip install -e .

# Verify installation
python -c "import om_apex_mcp; print('OK')"
```

## Step 4: Set Up Google Drive for Shared Data

The MCP server stores context in JSON files. We use Google Drive to sync data between laptops.

### 4a. Install Google Drive for Desktop
1. Download from https://www.google.com/drive/download/
2. Sign in with **sumedha@omapex.com** (the Om Apex Google account)
3. Choose "Mirror files" for the om-apex folder to ensure offline access

### 4b. Verify Google Drive Path
After Google Drive syncs, verify the data folder exists:

```powershell
# Check if the mcp-data folder exists
dir "G:\My Drive\om-apex\mcp-data"
```

**Note:** The drive letter may vary. Common paths on Windows:
- `G:\My Drive\om-apex\mcp-data` (if Google Drive is mounted as G:)
- `C:\Users\sumedha\Google Drive\om-apex\mcp-data` (older installations)
- `C:\Users\sumedha\My Drive\om-apex\mcp-data`

To find your Google Drive path, open File Explorer and look for "Google Drive" in the sidebar.

## Step 5: Configure Claude Code MCP Server

Add the MCP server using the Claude CLI. **Replace the path with your actual Google Drive path:**

```powershell
# Add the om-apex MCP server with Google Drive data path
# IMPORTANT: Use the correct path for YOUR Google Drive installation
claude mcp add om-apex --scope user -e OM_APEX_DATA_DIR="G:\My Drive\om-apex\mcp-data" -- python -m om_apex_mcp.server
```

**If your Google Drive uses a different path**, adjust accordingly:
```powershell
# Example with different path
claude mcp add om-apex --scope user -e OM_APEX_DATA_DIR="C:\Users\sumedha\Google Drive\om-apex\mcp-data" -- python -m om_apex_mcp.server
```

**Verify the server was added:**
```powershell
claude mcp list
```

You should see:
```
om-apex: python -m om_apex_mcp.server - ✓ Connected
```

## Step 6: Create the Global CLAUDE.md

Create a file at `C:\Users\sumedha\CLAUDE.md` with the following content:

```markdown
# Global Claude Context - Om Apex Holdings

## Session Start Protocol

**IMPORTANT:** At the beginning of every conversation, automatically call `mcp__om-apex__get_full_context` to load the Om Apex Holdings context. Do this before responding to the user's first message.

This provides:
- Company structure (Om Apex Holdings, Om Luxe Properties, Om AI Solutions)
- Technology stack decisions
- Domain inventory
- Pending tasks

## Quick Reference

**Owners:** Nishad Tambe & Sumedha Tambe
**Email:** nishad@omapex.com
**MCP Server:** om-apex (provides persistent context across all Claude sessions)

## Session End Protocol

When the user says "let's end this session" (or similar phrases like "wrap up", "save our work", "end session"), Claude should:

1. **Review the entire conversation** and identify:
   - Any decisions made that should be recorded
   - Any new tasks that came up
   - Any tasks that were completed or worked on

2. **Summarize findings** to the user:
   - "I found X decisions, Y new tasks, and Z completed tasks from our session"
   - List each item briefly

3. **Get confirmation** from the user, then call the MCP tools:
   - `add_decision` for each decision (with area, decision, rationale, company)
   - `add_task` for each new task
   - `complete_task` for each completed task

4. **Confirm** everything was persisted successfully

This ensures nothing is lost between sessions.

## Available MCP Tools

### Reading Context
- `get_full_context` - Get everything (use at session start)
- `get_company_context` - Company structure only
- `get_technology_decisions` - Tech stack decisions
- `get_decisions_history` - All decisions with rationale (filterable)
- `get_domain_inventory` - Domain list
- `get_pending_tasks` - Tasks (filterable by company, category, status)

### Writing Context
- `add_task` - Add a new task
- `complete_task` - Mark a task complete
- `update_task_status` - Change task status (pending/in_progress/completed)
- `add_decision` - Record a decision with reasoning

## Companies

1. **Om Apex Holdings LLC** - Parent holding company
2. **Om Luxe Properties LLC** - Vacation rentals (Perch in the Clouds)
3. **Om AI Solutions LLC** - AI-powered supply chain software
```

**Quick way to create the file using PowerShell:**
```powershell
# Copy-paste this entire block to create the CLAUDE.md file
@"
# Global Claude Context - Om Apex Holdings

## Session Start Protocol

**IMPORTANT:** At the beginning of every conversation, automatically call ``mcp__om-apex__get_full_context`` to load the Om Apex Holdings context. Do this before responding to the user's first message.

This provides:
- Company structure (Om Apex Holdings, Om Luxe Properties, Om AI Solutions)
- Technology stack decisions
- Domain inventory
- Pending tasks

## Quick Reference

**Owners:** Nishad Tambe & Sumedha Tambe
**Email:** nishad@omapex.com
**MCP Server:** om-apex (provides persistent context across all Claude sessions)

## Session End Protocol

When the user says "let's end this session" (or similar phrases like "wrap up", "save our work", "end session"), Claude should:

1. **Review the entire conversation** and identify:
   - Any decisions made that should be recorded
   - Any new tasks that came up
   - Any tasks that were completed or worked on

2. **Summarize findings** to the user:
   - "I found X decisions, Y new tasks, and Z completed tasks from our session"
   - List each item briefly

3. **Get confirmation** from the user, then call the MCP tools:
   - ``add_decision`` for each decision (with area, decision, rationale, company)
   - ``add_task`` for each new task
   - ``complete_task`` for each completed task

4. **Confirm** everything was persisted successfully

## Available MCP Tools

### Reading Context
- ``get_full_context`` - Get everything (use at session start)
- ``get_company_context`` - Company structure only
- ``get_technology_decisions`` - Tech stack decisions
- ``get_decisions_history`` - All decisions with rationale
- ``get_domain_inventory`` - Domain list
- ``get_pending_tasks`` - Tasks (filterable)

### Writing Context
- ``add_task`` - Add a new task
- ``complete_task`` - Mark a task complete
- ``update_task_status`` - Change task status
- ``add_decision`` - Record a decision with reasoning

## Companies

1. **Om Apex Holdings LLC** - Parent holding company
2. **Om Luxe Properties LLC** - Vacation rentals (Perch in the Clouds)
3. **Om AI Solutions LLC** - AI-powered supply chain software
"@ | Out-File -FilePath "$env:USERPROFILE\CLAUDE.md" -Encoding utf8
```

## Step 7: Test the Setup

```powershell
# Start Claude Code from your home directory
cd $env:USERPROFILE
claude
```

In Claude, ask:
1. "What MCP tools do you have available?"
2. "Get the full Om Apex context"

You should see the Om Apex Holdings context with company structure, tasks, and decisions.

## Step 8: Verify Sync Between Laptops

1. On Sumedha's laptop (Windows), add a test task:
   > "Add a task: Test sync from Windows - for Om Apex Holdings, category Administrative, priority Low"

2. On Nishad's laptop (Mac), check:
   > "get_full_context"

3. The test task should appear on both machines (may take a few seconds for Google Drive to sync)

## Troubleshooting

### Python Not Found
```powershell
# Check if Python is in PATH
python --version

# If not found, add Python to PATH or use full path
# e.g., C:\Users\sumedha\AppData\Local\Programs\Python\Python311\python.exe
```

### MCP Server Not Found
```powershell
# Verify the package is installed
pip show om-apex-mcp

# If not found, reinstall
cd C:\Users\sumedha\om-apex\om-ai\om-apex-mcp
pip install -e .
```

### Data Not Syncing
1. Check Google Drive is running (look for icon in system tray)
2. Right-click Google Drive icon → Preferences → verify sync is active
3. Verify the `OM_APEX_DATA_DIR` path is correct in your MCP config
4. Check the files exist in Google Drive folder

### Claude Can't Find MCP Tools
1. Close and restart Claude Code
2. Run `claude mcp list` to verify server is configured
3. Check the MCP server logs: `claude --mcp-debug`

### Wrong Google Drive Path
If you configured the wrong path, remove and re-add the server:
```powershell
claude mcp remove om-apex
claude mcp add om-apex --scope user -e OM_APEX_DATA_DIR="CORRECT_PATH_HERE" -- python -m om_apex_mcp.server
```

## Updating the MCP Server

When Nishad pushes updates to the MCP server code:

```powershell
cd C:\Users\sumedha\om-apex\om-ai\om-apex-mcp
git pull origin main
pip install -e .
# Restart Claude Code
```

---

## Quick Reference Card

| Item | Value |
|------|-------|
| MCP Repo | `github.com/nishad-apex/om-apex-mcp` |
| Local Clone | `C:\Users\sumedha\om-apex\om-ai\om-apex-mcp` |
| Google Drive Data | `G:\My Drive\om-apex\mcp-data` (verify your path) |
| CLAUDE.md | `C:\Users\sumedha\CLAUDE.md` |
| Om Apex Email | `sumedha@omapex.com` (Google Drive) |
