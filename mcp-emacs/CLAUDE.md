# MCP Emacs Server - Claude Guide

This document provides information for Claude about the MCP Emacs server.

## Tool Usage Guidelines

### Running Emacs Lisp Code

When using `run_emacsclient_code`, you do not need to wrap the code in quotes. The tool handles quoting and escaping for you.

**Example:**
```lisp
(with-current-buffer "my-buffer"
  (goto-char (point-min))
  (insert "Hello, world!"))
```

### Paths and Buffers

When specifying buffers, you can use either:
- Buffer names (e.g., `"*scratch*"`)
- File paths (e.g., `"/path/to/file.org"`)

### Patterns vs. Positions

For tools like `emacs_get_region` and `emacs_replace_region`, the `start` and `end` parameters can be either:
- Numeric positions (e.g., `"100"`)
- String patterns (e.g., `"## Section Header"`)

The server will handle both appropriately.

## Example Tool Calls

### Get Region
```
emacs_get_region(
    buffer="~/Documents/notes.org",
    start="# Project Ideas",
    end="# Next Steps"
)
```

### Insert Text
```
emacs_insert_at(
    buffer="~/Documents/notes.org",
    pattern="# Project Ideas",
    text="\n- New idea: Build an MCP server for X\n",
    after=true
)
```

### Replace Text
```
emacs_replace_region(
    buffer="~/Documents/notes.org",
    start="# Current Tasks",
    end="# Completed Tasks",
    old_text="[ ] Fix bug in Y",
    new_text="[X] Fix bug in Y"
)
```

### Get Org Properties
```
emacs_get_org_properties(
    buffer="~/org/todo.org",
    heading="Weekly Review"
)
```