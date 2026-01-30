# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities to: **nishad@omapex.com**

**Do NOT create public GitHub issues for security vulnerabilities.**

### Response Timeline

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 7 days
- **Resolution timeline:** Communicated after assessment

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Measures

This MCP server implements:

- Input validation on all tool parameters
- No secrets stored in code (uses environment variables)
- File access restricted to designated data directories
- No direct database connections (uses Supabase client with RLS)
- Google Calendar access uses OAuth service accounts

## Responsible Disclosure

We kindly ask that you:

- Give us reasonable time to fix the issue before public disclosure
- Avoid accessing or modifying other users' data
- Act in good faith to avoid privacy violations and service disruption

We appreciate your help in keeping Om Apex projects secure.
