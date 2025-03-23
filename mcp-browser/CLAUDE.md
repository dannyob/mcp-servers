# MCP Browser Assistant Guide

## Setup & Running

```bash
# Launch Brave browser with debugging port
brave --remote-debugging-port=9222

# Run the MCP browser server
uv run mcp-browser.py
```

## Testing

```bash
# Run specific test
pytest tests/test_name.py

# Run all tests
pytest
```

## Code Style Guidelines

- **Imports**: Standard library first, then third-party, then local modules
- **Type Annotations**: Use full type hints with Optional/Union from typing module
- **Error Handling**: Use try/except with specific exception types, log errors to stderr
- **Function Design**: Follow async patterns with clear docstrings in Google style
- **Naming**: Use snake_case for variables/functions, leading underscore for private items
- **Comments**: Explain complex logic or workarounds, especially for browser integration 
- **Global Variables**: Prefix with underscore, document purpose at declaration

## Browser Integration Notes

The MCP browser connects to an existing Brave browser instance via CDP.
Critical functions include page navigation, content extraction, and interaction.