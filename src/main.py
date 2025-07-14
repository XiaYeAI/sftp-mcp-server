#!/usr/bin/env python3
"""
SFTP MCP Server

A Model Context Protocol server that provides SFTP operations including:
- Directory synchronization
- Single file upload
- File reading
- Remote command execution

This server uses stdio transport for secure local communication.
"""

import os
import sys
import json
import asyncio
import fnmatch
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

import paramiko
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configuration from environment variables
TARGET_HOST = os.environ.get("TARGET_HOST")
TARGET_PORT = int(os.environ.get("TARGET_PORT", 22))
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
TARGET_PASSWORD = os.environ.get("TARGET_PASSWORD")
LOCAL_PATH = os.environ.get("LOCAL_PATH")
REMOTE_PATH = os.environ.get("REMOTE_PATH")

# Parse ignore patterns
ignore_patterns_str = os.environ.get("IGNORE_PATTERNS", "[]")
try:
    IGNORE_PATTERNS = json.loads(ignore_patterns_str)
except json.JSONDecodeError:
    IGNORE_PATTERNS = []

# Create FastMCP server instance
mcp = FastMCP("SFTP-MCP-Server")


def get_ssh_client():
    """Create and return an SSH client connection."""
    if not all([TARGET_HOST, TARGET_USERNAME, TARGET_PASSWORD]):
        raise ValueError("Missing required SFTP connection parameters")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=TARGET_HOST,
        port=TARGET_PORT,
        username=TARGET_USERNAME,
        password=TARGET_PASSWORD,
        timeout=15
    )
    return ssh


def is_ignored(path: str, ignore_patterns: List[str]) -> bool:
    """Check if a path should be ignored based on patterns."""
    normalized_path = path.replace('\\', '/')
    for pattern in ignore_patterns:
        normalized_pattern = pattern.replace('\\', '/')
        if normalized_pattern.endswith('/'):
            if (normalized_path + '/').startswith(normalized_pattern):
                return True
        else:
            if fnmatch.fnmatch(normalized_path, normalized_pattern) or \
               fnmatch.fnmatch(os.path.basename(normalized_path), normalized_pattern):
                return True
    return False


@mcp.tool()
def sync_directory(local_dir: Optional[str] = None, remote_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Synchronize a local directory to remote SFTP server.
    
    Args:
        local_dir: Local directory path (defaults to LOCAL_PATH env var)
        remote_dir: Remote directory path (defaults to REMOTE_PATH env var)
    
    Returns:
        Dictionary with sync results including uploaded files and any errors
    """
    local_path = local_dir or LOCAL_PATH
    remote_path = remote_dir or REMOTE_PATH
    
    if not local_path or not remote_path:
        return {"error": "Local and remote paths must be specified"}
    
    if not os.path.exists(local_path):
        return {"error": f"Local path does not exist: {local_path}"}
    
    try:
        ssh_client = get_ssh_client()
        sftp = ssh_client.open_sftp()
        
        results = {
            "uploaded_files": [],
            "created_directories": [],
            "ignored_items": [],
            "errors": []
        }
        
        # Ensure remote base directory exists
        current_path = ""
        for part in remote_path.split('/'):
            if not part:
                continue
            current_path += '/' + part
            try:
                sftp.stat(current_path)
            except FileNotFoundError:
                sftp.mkdir(current_path)
                results["created_directories"].append(current_path)
        
        # Walk through local directory
        for root, dirs, files in os.walk(local_path, topdown=True):
            # Filter ignored directories
            original_dirs = list(dirs)
            dirs[:] = [d for d in original_dirs 
                      if not is_ignored(os.path.join(os.path.relpath(root, local_path), d), IGNORE_PATTERNS)]
            
            for d in original_dirs:
                if d not in dirs:
                    results["ignored_items"].append(os.path.join(os.path.relpath(root, local_path), d) + '/')
            
            # Create remote directories
            for dirname in dirs:
                relative_dir_path = os.path.relpath(os.path.join(root, dirname), local_path)
                remote_dir_path = os.path.join(remote_path, relative_dir_path).replace('\\', '/')
                try:
                    sftp.stat(remote_dir_path)
                except FileNotFoundError:
                    sftp.mkdir(remote_dir_path)
                    results["created_directories"].append(remote_dir_path)
            
            # Upload files
            for filename in files:
                relative_file_path = os.path.relpath(os.path.join(root, filename), local_path)
                if is_ignored(relative_file_path, IGNORE_PATTERNS):
                    results["ignored_items"].append(relative_file_path)
                    continue
                
                local_file_path = os.path.join(root, filename)
                remote_file_path = os.path.join(remote_path, relative_file_path).replace('\\', '/')
                
                try:
                    sftp.put(local_file_path, remote_file_path)
                    results["uploaded_files"].append(relative_file_path)
                except Exception as e:
                    results["errors"].append(f"Failed to upload {relative_file_path}: {str(e)}")
        
        sftp.close()
        ssh_client.close()
        
        return results
        
    except Exception as e:
        return {"error": f"Sync failed: {str(e)}"}


@mcp.tool()
def upload_file(local_file_path: str, remote_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload a single file to the remote SFTP server.
    
    Args:
        local_file_path: Path to the local file to upload
        remote_file_path: Remote destination path (optional, will use same relative path)
    
    Returns:
        Dictionary with upload result
    """
    if not os.path.exists(local_file_path):
        return {"error": f"Local file does not exist: {local_file_path}"}
    
    if not os.path.isfile(local_file_path):
        return {"error": f"Path is not a file: {local_file_path}"}
    
    # Determine remote path
    if remote_file_path is None:
        if LOCAL_PATH and REMOTE_PATH:
            if local_file_path.startswith(LOCAL_PATH):
                relative_path = os.path.relpath(local_file_path, LOCAL_PATH)
                remote_file_path = os.path.join(REMOTE_PATH, relative_path).replace('\\', '/')
            else:
                return {"error": "Cannot determine remote path. Please specify remote_file_path."}
        else:
            return {"error": "Remote path not specified and no default paths configured."}
    
    try:
        ssh_client = get_ssh_client()
        sftp = ssh_client.open_sftp()
        
        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_file_path)
        if remote_dir:
            current_path = ""
            for part in remote_dir.split('/'):
                if not part:
                    continue
                current_path += '/' + part
                try:
                    sftp.stat(current_path)
                except FileNotFoundError:
                    sftp.mkdir(current_path)
        
        # Upload the file
        sftp.put(local_file_path, remote_file_path)
        
        # Get file info
        local_size = os.path.getsize(local_file_path)
        remote_stat = sftp.stat(remote_file_path)
        
        sftp.close()
        ssh_client.close()
        
        return {
            "success": True,
            "local_file": local_file_path,
            "remote_file": remote_file_path,
            "file_size": local_size,
            "uploaded_size": remote_stat.st_size
        }
        
    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}


@mcp.tool()
def read_remote_file(remote_file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Read the contents of a file from the remote SFTP server.
    
    Args:
        remote_file_path: Path to the remote file to read
        encoding: Text encoding to use (default: utf-8)
    
    Returns:
        Dictionary with file contents or error
    """
    try:
        ssh_client = get_ssh_client()
        sftp = ssh_client.open_sftp()
        
        with sftp.open(remote_file_path, 'r') as f:
            content = f.read().decode(encoding)
        
        # Get file stats
        stat = sftp.stat(remote_file_path)
        
        sftp.close()
        ssh_client.close()
        
        return {
            "success": True,
            "file_path": remote_file_path,
            "content": content,
            "file_size": stat.st_size,
            "encoding": encoding
        }
        
    except FileNotFoundError:
        return {"error": f"File not found on remote server: {remote_file_path}"}
    except UnicodeDecodeError as e:
        return {"error": f"Failed to decode file with {encoding} encoding: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to read remote file: {str(e)}"}


@mcp.tool()
def execute_remote_command(command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a command on the remote server via SSH.
    
    Args:
        command: Command to execute on the remote server
        working_directory: Optional working directory for the command
    
    Returns:
        Dictionary with command output, exit code, and any errors
    """
    try:
        ssh_client = get_ssh_client()
        
        # Prepare command with working directory if specified
        if working_directory:
            command = f"cd {working_directory} && {command}"
        
        # Execute command
        stdin, stdout, stderr = ssh_client.exec_command(command)
        
        # Get results
        exit_code = stdout.channel.recv_exit_status()
        stdout_content = stdout.read().decode('utf-8')
        stderr_content = stderr.read().decode('utf-8')
        
        ssh_client.close()
        
        return {
            "success": True,
            "command": command,
            "exit_code": exit_code,
            "stdout": stdout_content,
            "stderr": stderr_content,
            "working_directory": working_directory
        }
        
    except Exception as e:
        return {"error": f"Command execution failed: {str(e)}"}


@mcp.tool()
def list_remote_directory(remote_dir_path: str) -> Dict[str, Any]:
    """
    List contents of a remote directory.
    
    Args:
        remote_dir_path: Path to the remote directory to list
    
    Returns:
        Dictionary with directory contents
    """
    try:
        ssh_client = get_ssh_client()
        sftp = ssh_client.open_sftp()
        
        items = []
        for item in sftp.listdir_attr(remote_dir_path):
            items.append({
                "name": item.filename,
                "size": item.st_size,
                "is_directory": item.st_mode and (item.st_mode & 0o040000) != 0,
                "permissions": oct(item.st_mode)[-3:] if item.st_mode else None,
                "modified_time": item.st_mtime
            })
        
        sftp.close()
        ssh_client.close()
        
        return {
            "success": True,
            "directory": remote_dir_path,
            "items": items,
            "total_items": len(items)
        }
        
    except FileNotFoundError:
        return {"error": f"Directory not found: {remote_dir_path}"}
    except Exception as e:
        return {"error": f"Failed to list directory: {str(e)}"}


@mcp.resource("sftp://config")
def get_sftp_config() -> str:
    """
    Get current SFTP server configuration (without sensitive data).
    """
    config = {
        "host": TARGET_HOST,
        "port": TARGET_PORT,
        "username": TARGET_USERNAME,
        "local_path": LOCAL_PATH,
        "remote_path": REMOTE_PATH,
        "ignore_patterns": IGNORE_PATTERNS,
        "connection_status": "configured" if all([TARGET_HOST, TARGET_USERNAME, TARGET_PASSWORD]) else "incomplete"
    }
    return json.dumps(config, indent=2)


@mcp.prompt()
def sync_workflow() -> str:
    """
    A workflow prompt for synchronizing files to remote server.
    """
    return """
You are helping with SFTP file synchronization. Here's a typical workflow:

1. First, check the current configuration using the sftp://config resource
2. If syncing a full directory, use sync_directory tool
3. If uploading specific files, use upload_file tool for each file
4. You can read remote files using read_remote_file tool
5. Execute commands on remote server using execute_remote_command tool
6. List remote directories using list_remote_directory tool

Always confirm the operation details before proceeding with uploads or commands.
"""


@mcp.prompt()
def file_upload_guide() -> str:
    """
    A guide for uploading individual files.
    """
    return """
For uploading individual files:

1. Use upload_file tool with the local file path
2. Optionally specify the remote destination path
3. If no remote path is specified, the tool will use the configured LOCAL_PATH and REMOTE_PATH to determine the relative location
4. The tool will automatically create any necessary remote directories
5. Check the upload result for success confirmation and file size verification

Example: upload_file("/path/to/local/file.txt", "/remote/path/file.txt")
"""


if __name__ == "__main__":
    # Run the MCP server using stdio transport
    mcp.run()