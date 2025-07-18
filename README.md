# SFTP MCP Server

A Model Context Protocol (MCP) server that provides SFTP operations including directory synchronization, single file upload, file reading, and remote command execution. This server uses stdio transport for secure local communication.

## Project Structure

- `src/main.py`: MCP server implementation with SFTP tools, resources, and prompts
- `pyproject.toml`: Project metadata and dependencies
- `requirements.txt`: Python dependencies (legacy)

## Installation & Setup

This project uses Python. It is recommended to use a virtual environment.

1.  **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

2.  **Install dependencies:**

    This project provides a `requirements.txt` file to install all necessary dependencies. You can also use `uv` if you have it installed.

    *   **Using `pip` (recommended):**

        ```bash
        pip install -r requirements.txt
        ```

    *   **Using `uv`:**

        ```bash
        uv sync
        ```

2. Set up environment variables (create a `.env` file or set them in your environment):
   ```bash
   # SFTP target configuration
   TARGET_HOST=your-sftp-server.com
   TARGET_PORT=22
   TARGET_USERNAME=your-username
   TARGET_PASSWORD=your-password
   
   # Path configuration
   LOCAL_PATH=/path/to/local/directory
   REMOTE_PATH=/path/to/remote/directory
   
   # Optional: Ignore patterns (JSON array)
   IGNORE_PATTERNS=["*.log", "node_modules/", ".git/"]
   ```

## Running the Service

Once the dependencies are installed, you can start the MCP server.

*   **Using `python`:**

    ```bash
    python src/main.py
    ```

*   **Using `uv`:**

    ```bash
    uv run start
    ```

The server will run using stdio transport and communicate via JSON-RPC 2.0.

## MCP Client Configuration

To use this server with an MCP client, configure it as follows:

```json
{
  "mcpServers": {
    "sftp-server": {
      "command": "uv",
      "args": ["--directory", "/path/to/your/project", "run", "start"],
      "env": {
        "TARGET_HOST": "your-sftp-server.com",
        "TARGET_USERNAME": "your-username",
        "TARGET_PASSWORD": "your-password",
        "LOCAL_PATH": "/path/to/local/directory",
        "REMOTE_PATH": "/path/to/remote/directory"
      }
    }
  }
}
```

**Important Notes:**
- Replace `/path/to/your/project` with the absolute path to your project root directory
- The server uses stdio transport, so no network ports are exposed
- Environment variables can be set in the MCP client configuration or in a `.env` file

## MCP Tools

### sync_directory
Synchronize a local directory to remote SFTP server.

**Parameters:**
- `local_dir` (optional): Local directory path (defaults to LOCAL_PATH env var)
- `remote_dir` (optional): Remote directory path (defaults to REMOTE_PATH env var)

**Returns:** Dictionary with sync results including uploaded files, created directories, ignored items, and any errors.

### upload_file
Upload a single file to the remote SFTP server.

**Parameters:**
- `local_file_path`: Path to the local file to upload
- `remote_file_path` (optional): Remote destination path (auto-determined if not specified)

**Returns:** Dictionary with upload result including file sizes and paths.

### read_remote_file
Read the contents of a file from the remote SFTP server.

**Parameters:**
- `remote_file_path`: Path to the remote file to read
- `encoding` (optional): Text encoding to use (default: utf-8)

**Returns:** Dictionary with file contents, size, and encoding information.

### execute_remote_command
Execute a command on the remote server via SSH.

**Parameters:**
- `command`: Command to execute on the remote server
- `working_directory` (optional): Working directory for the command

**Returns:** Dictionary with command output, exit code, stdout, and stderr.

### list_remote_directory
List contents of a remote directory.

**Parameters:**
- `remote_dir_path`: Path to the remote directory to list

**Returns:** Dictionary with directory contents including file names, sizes, permissions, and types.

## MCP Resources

### sftp://config
Get current SFTP server configuration (without sensitive data).

Returns JSON with host, port, username, paths, ignore patterns, and connection status.

## MCP Prompts

### sync_workflow
A workflow prompt for synchronizing files to remote server. Provides step-by-step guidance for common SFTP operations.

### file_upload_guide
A guide for uploading individual files. Explains how to use the upload_file tool effectively.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `TARGET_HOST` | SFTP server hostname | Required |
| `TARGET_PORT` | SFTP server port | `22` |
| `TARGET_USERNAME` | SFTP username | Required |
| `TARGET_PASSWORD` | SFTP password | Required |
| `LOCAL_PATH` | Local directory to sync | Required |
| `REMOTE_PATH` | Remote directory destination | Required |
| `IGNORE_PATTERNS` | JSON array of ignore patterns | `[]` |

## Features

- **Standard MCP Protocol**: Full compliance with MCP specification using JSON-RPC 2.0
- **Stdio Transport**: Secure local communication without network exposure
- **Directory Synchronization**: Sync entire directories with ignore patterns support
- **Single File Upload**: Upload individual files with automatic path resolution
- **Remote File Reading**: Read file contents from remote server with encoding support
- **Remote Command Execution**: Execute commands on remote server via SSH
- **Directory Listing**: Browse remote directory contents with detailed file information
- **Environment Configuration**: Flexible setup via environment variables
- **Secure Authentication**: Uses stdio transport, no API keys needed
- **Error Handling**: Comprehensive error reporting for all operations

## Usage Examples

### Sync entire directory
```python
# Uses configured LOCAL_PATH and REMOTE_PATH
sync_directory()

# Or specify custom paths
sync_directory("/custom/local/path", "/custom/remote/path")
```

### Upload single file
```python
# Auto-determine remote path based on LOCAL_PATH/REMOTE_PATH
upload_file("/local/path/file.txt")

# Specify exact remote destination
upload_file("/local/path/file.txt", "/remote/path/file.txt")
```

### Read remote file
```python
# Read with default UTF-8 encoding
read_remote_file("/remote/path/file.txt")

# Specify encoding
read_remote_file("/remote/path/file.txt", "latin-1")
```

### Execute remote command
```python
# Simple command
execute_remote_command("ls -la")

# Command with working directory
execute_remote_command("npm install", "/var/www/myapp")
```

### List remote directory
```python
list_remote_directory("/remote/path")
```

## Security Considerations

- The server uses stdio transport, eliminating network security concerns
- SFTP credentials are passed via environment variables
- No sensitive data is exposed in logs or responses
- All file operations are restricted to configured paths
- SSH connections use paramiko with proper host key handling

## Troubleshooting

### Connection Issues
- Verify TARGET_HOST, TARGET_USERNAME, and TARGET_PASSWORD are correct
- Check if the SFTP server is accessible from your network
- Ensure TARGET_PORT is correct (default is 22)

### Path Issues
- Verify LOCAL_PATH exists and is readable
- Ensure REMOTE_PATH exists on the remote server
- Check file permissions on both local and remote systems

### Ignore Patterns
- IGNORE_PATTERNS must be valid JSON array format
- Patterns support Unix-style wildcards (*, ?, [])
- Directory patterns should end with `/`

## Migration from v1.x

If you're upgrading from the previous FastAPI-based version:

1. Update your MCP client configuration to remove HTTP-specific settings
2. Remove APP_HOST, APP_PORT, and MCP_SECRET_TOKEN environment variables
3. The server now uses stdio transport instead of HTTP
4. All endpoints are now MCP tools instead of REST API endpoints
5. Real-time progress streaming is replaced with synchronous tool responses

The core functionality remains the same, but the interface has changed to comply with MCP standards.