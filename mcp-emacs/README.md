# MCP Emacs Server

A FastMCP implementation of Emacs integration tools, ported from JavaScript to Python.

## Overview

This MCP server provides tools for interacting with Emacs from an LLM, allowing operations like:

- Running shell commands
- Executing Emacs Lisp code
- Getting text regions from Emacs buffers
- Inserting and replacing text in Emacs buffers
- Working with org-mode properties

## Requirements

- Python 3.10 or higher
- Emacs with an active server (run with `emacs --daemon` or use an existing Emacs session)
- `uv` (Python package manager)

## Installation

You can run the server directly without installation using `uv`:

```bash
uv run mcp-emacs.py
```

Or install dependencies manually:

```bash
pip install mcp[cli]
```

## Usage

1. Start your Emacs server if not already running:
   ```bash
   emacs --daemon
   ```

2. Run the MCP server:
   ```bash
   python mcp-emacs.py
   ```

3. Connect to the server using an MCP-compatible client, such as Claude.

## Available Tools

The server provides the following tools:

- **run_command**: Execute shell commands
- **run_emacsclient_code**: Run arbitrary Emacs Lisp code
- **emacs_get_region**: Get text from a specified region
- **emacs_insert_at**: Insert text at a specific position
- **emacs_replace_region**: Replace text in a region
- **emacs_get_org_properties**: Get properties from an org-mode heading

## Prompts

- **include_command_output**: Run a command and include its output as context