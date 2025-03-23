#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]"
# ]
# ///
# This script provides MCP server functionality for Emacs, ported from JavaScript version
import asyncio
import subprocess
import shlex
import sys
from typing import Optional, Union, Any, Dict, List, Tuple
from mcp.server import FastMCP

# Create an MCP server for Emacs integration
mcp = FastMCP("Emacs Integration")

class ExecError(Exception):
    """Error raised when a command execution fails."""
    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(self.message)

async def exec_async(command: str) -> Tuple[str, str]:
    """
    Execute a command asynchronously and return stdout and stderr.
    Similar to JavaScript's promisify(exec) function.
    """
    try:
        # Use shlex.split for proper argument parsing
        args = shlex.split(command)
        
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for the command to complete and get output
        stdout, stderr = await process.communicate()
        
        # Convert bytes to string
        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        
        # Check return code
        if process.returncode != 0:
            raise ExecError(
                f"Command failed with exit code {process.returncode}",
                stdout_str,
                stderr_str
            )
            
        return stdout_str, stderr_str
        
    except Exception as e:
        if isinstance(e, ExecError):
            raise e
        raise ExecError(str(e))

def escape_lisp_for_emacsclient(code: str) -> str:
    """
    Escapes Lisp code for safe execution via emacsclient.
    Handles single quote escaping since the code is wrapped in single quotes.
    """
    escaped_code = code.replace("'", "''")
    return f"'{escaped_code}'"

@mcp.tool()
async def run_command(command: str, context: Optional[Any] = None) -> Dict[str, str]:
    """
    Executes a zsh command on the local machine. Use for system operations, file inspection, or utilities. 
    Commands run with user permissions.
    
    Args:
        command: Line to run. Not escaped. If the command fails, consider how you escaped it.
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary with stdout and stderr output
    """
    if not command:
        raise ValueError("Command is required")
    
    try:
        stdout, stderr = await exec_async(command)
        return {
            "STDOUT": stdout,
            "STDERR": stderr
        }
    except ExecError as error:
        return {
            "ERROR": error.message,
            "STDERR": error.stderr,
            "STDOUT": error.stdout
        }

@mcp.tool()
async def run_emacsclient_code(code: str, context: Optional[Any] = None) -> Dict[str, str]:
    """
    Executes Emacs Lisp code via emacsclient. Useful functions include (ai-add-journal text) 
    to add entries to onebig.org. No need to quote or escape the code.
    
    Args:
        code: Code. This is wrapped with single quotes and fed to emacsclient -e. 
              Single quotes are escaped. YOU DO NOT NEED TO WRAP THE CODE IN QUOTES.
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary with stdout and stderr output
    """
    if not code:
        raise ValueError("Code is required")
    
    try:
        escaped_code = escape_lisp_for_emacsclient(code)
        stdout, stderr = await exec_async(f"emacsclient -e {escaped_code}")
        return {
            "STDOUT": stdout,
            "STDERR": stderr
        }
    except ExecError as error:
        return {
            "ERROR": error.message,
            "STDERR": error.stderr,
            "STDOUT": error.stdout
        }

@mcp.tool()
async def emacs_get_region(
    buffer: str, 
    start: str, 
    end: str, 
    context: Optional[Any] = None
) -> Dict[str, str]:
    """
    Retrieves text from an Emacs buffer between specified points or patterns. 
    This is read-only and won't modify the buffer.
    
    Args:
        buffer: Buffer or file name to read from
        start: Start position - either a number or a string pattern
        end: End position - either a number or a string pattern
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary with stdout and stderr output
    """
    if not buffer or not start or not end:
        raise ValueError("Buffer, start and end positions are required")
    
    try:
        code = f"""
(with-current-buffer "{buffer}"
  (let ((start-pos (if (string-match-p "^[0-9]+$" "{start}")
                      (string-to-number "{start}")
                    (save-excursion
                      (goto-char (point-min))
                      (search-forward "{start}" nil t)
                      (match-beginning 0))))
        (end-pos (if (string-match-p "^[0-9]+$" "{end}")
                    (string-to-number "{end}")
                  (save-excursion
                    (goto-char (point-min))
                    (search-forward "{end}" nil t)
                    (match-end 0)))))
    (when (and start-pos end-pos)
      (buffer-substring-no-properties start-pos end-pos))))"""
        
        stdout, stderr = await exec_async(f"emacsclient -e {escape_lisp_for_emacsclient(code)}")
        return {
            "STDOUT": stdout,
            "STDERR": stderr
        }
    except ExecError as error:
        return {
            "ERROR": error.message,
            "STDERR": error.stderr,
            "STDOUT": error.stdout
        }

@mcp.tool()
async def emacs_insert_at(
    buffer: str, 
    pattern: str, 
    text: str, 
    after: bool = True, 
    context: Optional[Any] = None
) -> Dict[str, str]:
    """
    Inserts text at a specific location in an Emacs buffer. 
    Finds the pattern and inserts before/after it. Saves the buffer after insertion.
    
    Args:
        buffer: Buffer or file name to modify
        pattern: Pattern to search for
        text: Text to insert
        after: If true, insert after pattern; if false, insert before
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary with stdout and stderr output
    """
    if not buffer or not pattern or not text:
        raise ValueError("Buffer, pattern and text are required")
    
    try:
        code = f"""
(with-current-buffer "{buffer}"
  (save-excursion
    (goto-char (point-min))
    (when (search-forward "{pattern}" nil t)
      (if {str(after).lower()}
          (goto-char (match-end 0))
        (goto-char (match-beginning 0)))
      (insert "{text}")
      (save-buffer))))"""
        
        stdout, stderr = await exec_async(f"emacsclient -e {escape_lisp_for_emacsclient(code)}")
        return {
            "STDOUT": stdout,
            "STDERR": stderr
        }
    except ExecError as error:
        return {
            "ERROR": error.message,
            "STDERR": error.stderr,
            "STDOUT": error.stdout
        }

@mcp.tool()
async def emacs_replace_region(
    buffer: str, 
    start: str, 
    end: str, 
    old_text: str, 
    new_text: str, 
    context: Optional[Any] = None
) -> Dict[str, str]:
    """
    Replaces text in a specified region of an Emacs buffer. 
    Finds and replaces all occurrences of old_text with new_text within the region. 
    Saves after changes.
    
    Args:
        buffer: Buffer or file name to modify
        start: Start of region - number or pattern
        end: End of region - number or pattern
        old_text: Text to replace
        new_text: Replacement text
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary with stdout and stderr output
    """
    if not buffer or not start or not end or not old_text or new_text is None:
        raise ValueError("Buffer, start, end, old_text and new_text are required")
    
    try:
        code = f"""
(with-current-buffer "{buffer}"
  (let ((start-pos (if (string-match-p "^[0-9]+$" "{start}")
                      (string-to-number "{start}")
                    (save-excursion
                      (goto-char (point-min))
                      (search-forward "{start}" nil t)
                      (match-beginning 0))))
        (end-pos (if (string-match-p "^[0-9]+$" "{end}")
                    (string-to-number "{end}")
                  (save-excursion
                    (goto-char (point-min))
                    (search-forward "{end}" nil t)
                    (match-end 0)))))
    (when (and start-pos end-pos)
      (save-excursion
        (goto-char start-pos)
        (while (search-forward "{old_text}" end-pos t)
          (replace-match "{new_text}" t t)))
      (save-buffer))))"""
        
        stdout, stderr = await exec_async(f"emacsclient -e {escape_lisp_for_emacsclient(code)}")
        return {
            "STDOUT": stdout,
            "STDERR": stderr
        }
    except ExecError as error:
        return {
            "ERROR": error.message,
            "STDERR": error.stderr,
            "STDOUT": error.stdout
        }

@mcp.tool()
async def emacs_get_org_properties(
    buffer: str, 
    heading: str, 
    context: Optional[Any] = None
) -> Dict[str, str]:
    """
    Retrieves all properties (metadata like SCHEDULED, DEADLINE, etc.) from an org-mode heading. 
    Returns properties as a structured list.
    
    Args:
        buffer: Org file to read from
        heading: Heading text to find
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary with stdout and stderr output
    """
    if not buffer or not heading:
        raise ValueError("Buffer and heading are required")
    
    try:
        code = f"""
(with-current-buffer "{buffer}"
  (save-excursion
    (goto-char (point-min))
    (when (re-search-forward (concat "^\\\\*+ " (regexp-quote "{heading}")) nil t)
      (org-entry-properties nil 'all))))"""
        
        stdout, stderr = await exec_async(f"emacsclient -e {escape_lisp_for_emacsclient(code)}")
        return {
            "STDOUT": stdout,
            "STDERR": stderr
        }
    except ExecError as error:
        return {
            "ERROR": error.message,
            "STDERR": error.stderr,
            "STDOUT": error.stdout
        }

@mcp.prompt()
async def include_command_output(command: str) -> List[Dict[str, Any]]:
    """
    Executes a command and formats its output (stdout/stderr) as a conversation 
    to provide context for your response.
    
    Args:
        command: Command to run
        
    Returns:
        Messages formatted for conversation context
    """
    if not command:
        raise ValueError("Command is required")
    
    try:
        stdout, stderr = await exec_async(command)
        
        messages = [
            {
                "role": "user",
                "content": f"I ran the following command, if there is any output it will be shown below:\n{command}"
            }
        ]
        
        if stdout:
            messages.append({
                "role": "user",
                "content": "STDOUT:\n" + stdout
            })
        
        if stderr:
            messages.append({
                "role": "user",
                "content": "STDERR:\n" + stderr
            })
        
        return messages
    except ExecError as error:
        messages = [
            {
                "role": "user",
                "content": f"I ran the following command, but it failed:\n{command}"
            },
            {
                "role": "user",
                "content": f"ERROR:\n{error.message}"
            }
        ]
        
        if error.stderr:
            messages.append({
                "role": "user",
                "content": "STDERR:\n" + error.stderr
            })
            
        if error.stdout:
            messages.append({
                "role": "user",
                "content": "STDOUT:\n" + error.stdout
            })
            
        return messages

@mcp.resource(uri="emacs-buffer:{buffer}")
async def emacs_buffer(buffer: str) -> Dict[str, str]:
    """
    Returns the full contents of an Emacs buffer. Particularly useful for accessing 
    org-mode files like onebig.org.
    
    Args:
        buffer: Buffer or file name to read from
        
    Returns:
        Dictionary with buffer content
    """
    if not buffer:
        raise ValueError("Buffer name is required")
    
    try:
        code = f"""
(with-current-buffer "{buffer}"
  (buffer-substring-no-properties (point-min) (point-max)))"""
        
        stdout, stderr = await exec_async(f"emacsclient -e {escape_lisp_for_emacsclient(code)}")
        return {
            "content": stdout.strip('"'),  # Remove outer quotes from the Emacs Lisp string output
            "buffer": buffer
        }
    except ExecError as error:
        return {
            "error": error.message,
            "stderr": error.stderr,
            "stdout": error.stdout
        }

def main():
    """Main entry point for the MCP server."""
    try:
        print("Starting Emacs MCP server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Error running MCP server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
