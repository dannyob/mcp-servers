#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]"
# ]
# ///
# This script provides MCP server functionality for shell commands
import asyncio
import subprocess
import shlex
import sys
from typing import Optional, Union, Any, Dict, List, Tuple
from mcp.server import FastMCP

# Create an MCP server for shell command integration
mcp = FastMCP("Shell Integration")

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
    Uses shell processing to support shell expressions and command chaining.
    """
    try:
        # Create subprocess with shell processing to properly handle shell expressions
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            executable="/bin/zsh"  # Explicitly use zsh
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

def main():
    """Main entry point for the MCP server."""
    try:
        print("Starting Shell MCP server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Error running MCP server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()