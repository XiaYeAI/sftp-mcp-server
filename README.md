# SFTP MCP 服务器

一个模型上下文协议（MCP）服务器，提供 SFTP 操作功能，包括目录同步、单文件上传、文件读取和远程命令执行。该服务器使用 stdio 传输方式进行安全的本地通信。

## 项目结构

- `src/main.py`: MCP 服务器实现，包含 SFTP 工具、资源和提示
- `pyproject.toml`: 项目元数据和依赖项
- `requirements.txt`: Python 依赖项

## 安装与设置

本项目使用 Python。**注意：MCP 服务器由 MCP 客户端（如 Claude Desktop）直接调用，通常不需要手动激活虚拟环境。**

### 方法一：使用 pip 安装依赖（推荐）

```bash
pip install -r requirements.txt
```

### 方法二：使用 uv 安装依赖

如果您安装了 `uv`，也可以使用：

```bash
uv sync
```

### 环境变量配置

所有配置都通过 MCP 客户端的环境变量进行设置，无需创建 `.env` 文件。

## 运行服务

**重要提示：** MCP 服务器通常不需要手动运行。它们由 MCP 客户端自动启动和管理。

如果需要手动测试，可以使用以下命令：

```bash
uv run python src/main.py
```

服务器将使用 stdio 传输方式运行，并通过 JSON-RPC 2.0 进行通信。

## MCP 客户端配置

要在 MCP 客户端中使用此服务器，请按以下方式配置：

```json
{
  "mcpServers": {
    "sftp-server": {
      "command": "uv",
       "args": ["--directory", "/path/to/your/project", "run", "python", "src/main.py"],
      "env": {
         "TARGET_HOST": "your-sftp-server.com",
         "TARGET_USERNAME": "your-username",
         "TARGET_PASSWORD": "your-password",
         "LOCAL_PATH": "/path/to/local/directory",
         "REMOTE_PATH": "/path/to/remote/directory",
         "IGNORE_PATTERNS": "[\"*.log\", \"node_modules/\", \".git/\"]"
       }
    }
  }
}
```

**重要说明：**
- 将 `/path/to/your/project` 替换为您的项目根目录的绝对路径
- 服务器使用 stdio 传输，因此不会暴露网络端口
- 环境变量可以在 MCP 客户端配置中设置，或在 `.env` 文件中设置

## MCP 工具

### sync_directory
将本地目录同步到远程 SFTP 服务器。

**参数：**
- `local_dir`（可选）：本地目录路径（默认使用 LOCAL_PATH 环境变量）
- `remote_dir`（可选）：远程目录路径（默认使用 REMOTE_PATH 环境变量）

**返回：** 包含同步结果的字典，包括上传的文件、创建的目录、忽略的项目和任何错误。

### upload_file
上传单个文件到远程 SFTP 服务器。

**参数：**
- `local_file_path`：要上传的本地文件路径
- `remote_file_path`（可选）：远程目标路径（如果未指定则自动确定）

**返回：** 包含上传结果的字典，包括文件大小和路径。

### read_remote_file
从远程 SFTP 服务器读取文件内容。

**参数：**
- `remote_file_path`：要读取的远程文件路径
- `encoding`（可选）：使用的文本编码（默认：utf-8）

**返回：** 包含文件内容、大小和编码信息的字典。

### execute_remote_command
通过 SSH 在远程服务器上执行命令。

**参数：**
- `command`：在远程服务器上执行的命令
- `working_directory`（可选）：命令的工作目录

**返回：** 包含命令输出、退出代码、stdout 和 stderr 的字典。

### list_remote_directory
列出远程目录的内容。

**参数：**
- `remote_dir_path`：要列出的远程目录路径

**返回：** 包含目录内容的字典，包括文件名、大小、权限和类型。

## MCP 资源

### sftp://config
获取当前 SFTP 服务器配置（不包含敏感数据）。

返回包含主机、端口、用户名、路径、忽略模式和连接状态的 JSON。

## MCP 提示

### sync_workflow
用于将文件同步到远程服务器的工作流提示。为常见的 SFTP 操作提供分步指导。

### file_upload_guide
上传单个文件的指南。解释如何有效使用 upload_file 工具。

## 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `TARGET_HOST` | SFTP 服务器主机名或 IP 地址 | 必需 |
| `TARGET_USERNAME` | SFTP 用户名 | 必需 |
| `TARGET_PASSWORD` | SFTP 密码 | 必需 |
| `LOCAL_PATH` | 本地目录路径 | 必需 |
| `REMOTE_PATH` | 远程目录路径 | 必需 |
| `IGNORE_PATTERNS` | 要忽略的文件模式 | `[]` |

## 功能特性

- **标准 MCP 协议**：完全符合 MCP 规范，使用 JSON-RPC 2.0
- **Stdio 传输**：安全的本地通信，无网络暴露
- **目录同步**：支持忽略模式的完整目录同步
- **单文件上传**：具有自动路径解析的单个文件上传
- **远程文件读取**：支持编码的远程服务器文件内容读取
- **远程命令执行**：通过 SSH 在远程服务器上执行命令
- **目录列表**：浏览远程目录内容，包含详细文件信息
- **环境配置**：通过环境变量进行灵活设置
- **安全认证**：使用 stdio 传输，无需 API 密钥
- **错误处理**：所有操作的全面错误报告

## 使用示例

### 同步整个目录
```python
# 使用配置的 LOCAL_PATH 和 REMOTE_PATH
sync_directory()

# 或指定自定义路径
sync_directory("/custom/local/path", "/custom/remote/path")
```

### 上传单个文件
```python
# 基于 LOCAL_PATH/REMOTE_PATH 自动确定远程路径
upload_file("/local/path/file.txt")

# 指定确切的远程目标
upload_file("/local/path/file.txt", "/remote/path/file.txt")
```

### 读取远程文件
```python
# 使用默认 UTF-8 编码读取
read_remote_file("/remote/path/file.txt")

# 指定编码
read_remote_file("/remote/path/file.txt", "latin-1")
```

### 执行远程命令
```python
# 简单命令
execute_remote_command("ls -la")

# 带工作目录的命令
execute_remote_command("npm install", "/var/www/myapp")
```

### 列出远程目录
```python
list_remote_directory("/remote/path")
```

## 安全考虑

- 服务器使用 stdio 传输，消除了网络安全问题
- SFTP 凭据通过环境变量传递
- 日志或响应中不会暴露敏感数据
- 所有文件操作都限制在配置的路径内
- SSH 连接使用 paramiko，具有适当的主机密钥处理

## 故障排除

### 连接问题
- 验证 TARGET_HOST、TARGET_USERNAME 和 TARGET_PASSWORD 是否正确
- 检查 SFTP 服务器是否可从您的网络访问
- 确保 TARGET_PORT 正确（默认为 22）

### 路径问题
- 验证 LOCAL_PATH 存在且可读
- 确保 REMOTE_PATH 在远程服务器上存在
- 检查本地和远程系统的文件权限

### 忽略模式
- IGNORE_PATTERNS 必须是有效的 JSON 数组格式
- 模式支持 Unix 风格的通配符（*、?、[]）
- 目录模式应以 `/` 结尾