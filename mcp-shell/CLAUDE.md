# MCP Shell Server - Claude Guide

This document provides information for Claude about the MCP Shell server.

## Tool Usage Guidelines

### Running Shell Commands

The `run_command` tool allows executing shell commands on the local machine with user permissions.

**Example:**
```bash
run_command(command="ls -la ~/Documents")
```

### Including Command Output in Context

The `include_command_output` prompt formatter executes a command and formats its output (stdout/stderr) as conversation context messages.

**Example:**
```bash
include_command_output(command="git status")
```

## Setup & Running

```bash
# Run the MCP shell server
uv run mcp-shell.py
```

## Code Style Guidelines

- **Imports**: Standard library first, then third-party, then local modules
- **Type Annotations**: Use full type hints with Optional/Union from typing module
- **Error Handling**: Use try/except with specific exception types, log errors to stderr
- **Function Design**: Follow async patterns with clear docstrings in Google style
- **Naming**: Use snake_case for variables/functions, leading underscore for private items
- **Comments**: Explain complex logic or workarounds
- **Global Variables**: Prefix with underscore, document purpose at declaration

## Example Tool Calls

### Run Command
```
run_command(
    command="find . -name '*.py' | grep 'test'"
)
```

### Include Command Output
```
include_command_output(
    command="ps aux | grep python"
)
```

## Security Notes

- Commands run with the same permissions as the MCP server process
- Avoid commands that might expose sensitive information or modify critical system files
- Consider the security implications of user-provided commands