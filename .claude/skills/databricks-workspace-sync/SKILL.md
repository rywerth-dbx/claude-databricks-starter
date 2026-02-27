---
name: databricks-workspace-sync
description: Upload and download files and directories to/from Databricks workspace. Use when syncing code, notebooks, or scripts between local development and workspace, or managing workspace files.
---

# Databricks Workspace Sync

## Overview

This skill helps you upload and download files and directories to/from Databricks workspace using the Databricks CLI. Supports Python scripts, notebooks, SQL files, and other workspace resources with automatic format handling.

## Workflow

### ⚠️ Important: CLI Syntax

The Databricks CLI uses `import` (NOT `upload`) and requires specific argument order:

**Correct syntax:**
```bash
databricks workspace import TARGET_PATH --file SOURCE_FILE [FLAGS]
```

**Key points:**
- Command is `import`, not `upload`
- Target path is positional argument (workspace destination)
- Source file uses `--file` flag
- `--overwrite` flag prevents "already exists" errors

### 1. Upload Single File

Upload a file to the workspace:

```bash
# Upload Python script
databricks workspace import /Workspace/Users/user@example.com/script.py --file /path/to/local/script.py --language PYTHON

# Upload SQL file
databricks workspace import /Workspace/Users/user@example.com/query.sql --file /path/to/local/query.sql --language SQL

# Upload Jupyter notebook
databricks workspace import /Workspace/Users/user@example.com/notebook --file /path/to/local/notebook.ipynb --format JUPYTER
```

**Interactive upload:**

```bash
# Prompt for local file
read -p "Enter local file path: " LOCAL_FILE

# Prompt for workspace path
read -p "Enter workspace destination path: " WORKSPACE_PATH

# Detect format and upload
if [[ "$LOCAL_FILE" == *.py ]]; then
    databricks workspace import "$WORKSPACE_PATH" --file "$LOCAL_FILE" --language PYTHON
elif [[ "$LOCAL_FILE" == *.sql ]]; then
    databricks workspace import "$WORKSPACE_PATH" --file "$LOCAL_FILE" --language SQL
elif [[ "$LOCAL_FILE" == *.ipynb ]]; then
    databricks workspace import "$WORKSPACE_PATH" --file "$LOCAL_FILE" --format JUPYTER
else
    databricks workspace import "$WORKSPACE_PATH" --file "$LOCAL_FILE" --format AUTO
fi

echo "✅ Uploaded $LOCAL_FILE to $WORKSPACE_PATH"
```

### 2. Upload Directory

Upload an entire directory to the workspace:

```bash
# Upload directory recursively
databricks workspace import-dir /path/to/local/dir /Workspace/Users/user@example.com/project --overwrite

# Upload without overwriting existing files
databricks workspace import-dir /path/to/local/dir /Workspace/Users/user@example.com/project
```

**Interactive directory upload:**

```bash
# Prompt for local directory
read -p "Enter local directory path: " LOCAL_DIR

# Prompt for workspace path
read -p "Enter workspace destination path: " WORKSPACE_PATH

# Confirm overwrite
read -p "Overwrite existing files? (y/n): " OVERWRITE

if [[ "$OVERWRITE" == "y" ]]; then
    databricks workspace import-dir "$LOCAL_DIR" "$WORKSPACE_PATH" --overwrite
else
    databricks workspace import-dir "$LOCAL_DIR" "$WORKSPACE_PATH"
fi

echo "✅ Uploaded directory $LOCAL_DIR to $WORKSPACE_PATH"
```

### 3. Download Files

Download files from the workspace to local:

```bash
# Download single file
databricks workspace export /Workspace/Users/user@example.com/notebook /path/to/local/notebook.py --format SOURCE

# Download directory
databricks workspace export-dir /Workspace/Users/user@example.com/project /path/to/local/dir
```

**Interactive download:**

```bash
# Prompt for workspace path
read -p "Enter workspace path to download: " WORKSPACE_PATH

# Prompt for local destination
read -p "Enter local destination path: " LOCAL_PATH

# Check if it's a directory or file
TYPE=$(databricks workspace get-status "$WORKSPACE_PATH" --output json | jq -r '.object_type')

if [[ "$TYPE" == "DIRECTORY" ]]; then
    databricks workspace export-dir "$WORKSPACE_PATH" "$LOCAL_PATH"
    echo "✅ Downloaded directory from $WORKSPACE_PATH to $LOCAL_PATH"
else
    databricks workspace export "$WORKSPACE_PATH" "$LOCAL_PATH" --format SOURCE
    echo "✅ Downloaded file from $WORKSPACE_PATH to $LOCAL_PATH"
fi
```

### 4. File Formats

Different formats for different use cases:

**SOURCE (Default for .py, .sql):**
- Preserves source code as-is
- Best for Python scripts and SQL files
- Can be edited directly in workspace

```bash
databricks workspace import /Workspace/Users/user@example.com/script.py --file script.py --format SOURCE
```

**JUPYTER (for .ipynb):**
- Imports Jupyter notebooks
- Preserves cell structure and outputs
- Best for notebook-based development

```bash
databricks workspace import /Workspace/Users/user@example.com/notebook --file notebook.ipynb --format JUPYTER
```

**HTML (for exports):**
- Exports as HTML
- Good for sharing or documentation
- Read-only format

```bash
databricks workspace export /Workspace/Users/user@example.com/notebook output.html --format HTML
```

**DBC (for archives):**
- Databricks archive format
- Contains multiple notebooks
- Good for backups

```bash
databricks workspace export-dir /Workspace/Users/user@example.com/project project.dbc --format DBC
```

### 5. Using Profiles

Work with multiple workspaces:

```bash
# Upload to dev workspace
databricks workspace import /Workspace/Users/user@example.com/script.py --file script.py --profile dev

# Upload to prod workspace
databricks workspace import /Workspace/Users/user@example.com/script.py --file script.py --profile prod
```

**Interactive profile selection:**

```bash
# List available profiles
databricks auth profiles

# Prompt for profile
read -p "Enter profile name (or press Enter for DEFAULT): " PROFILE

# Upload with profile
if [[ -n "$PROFILE" ]]; then
    databricks workspace import "$WORKSPACE_PATH" --file "$LOCAL_FILE" --profile "$PROFILE"
else
    databricks workspace import "$WORKSPACE_PATH" --file "$LOCAL_FILE"
fi
```

## Common Operations

### Sync Project Directory

Upload your entire project to workspace:

```bash
#!/bin/bash

# Configuration
LOCAL_PROJECT="/path/to/my/project"
WORKSPACE_BASE="/Workspace/Users/$(whoami)/projects"

# Prompt for project name
read -p "Enter project name: " PROJECT_NAME

# Create workspace directory if needed
databricks workspace mkdirs "$WORKSPACE_BASE/$PROJECT_NAME"

# Upload project
databricks workspace import-dir "$LOCAL_PROJECT" "$WORKSPACE_BASE/$PROJECT_NAME" --overwrite

echo "✅ Project synced to $WORKSPACE_BASE/$PROJECT_NAME"
```

### Download Workspace for Backup

Download workspace content for backup:

```bash
#!/bin/bash

# Prompt for workspace path
read -p "Enter workspace path to backup: " WORKSPACE_PATH

# Create backup directory with timestamp
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Download
databricks workspace export-dir "$WORKSPACE_PATH" "$BACKUP_DIR"

echo "✅ Backup created at $BACKUP_DIR"
```

### Upload Notebook with Dependencies

Upload a notebook and its dependencies:

```bash
#!/bin/bash

# Prompt for base path
read -p "Enter local project directory: " LOCAL_DIR
read -p "Enter workspace destination: " WORKSPACE_PATH

# Upload main notebooks
echo "Uploading notebooks..."
find "$LOCAL_DIR" -name "*.ipynb" -type f | while read notebook; do
    rel_path="${notebook#$LOCAL_DIR/}"
    workspace_dest="$WORKSPACE_PATH/${rel_path%.ipynb}"
    databricks workspace import "$workspace_dest" --file "$notebook" --format JUPYTER --overwrite
    echo "  ✅ $rel_path"
done

# Upload Python modules
echo "Uploading Python modules..."
find "$LOCAL_DIR" -name "*.py" -type f | while read script; do
    rel_path="${script#$LOCAL_DIR/}"
    workspace_dest="$WORKSPACE_PATH/$rel_path"
    databricks workspace import "$workspace_dest" --file "$script" --language PYTHON --overwrite
    echo "  ✅ $rel_path"
done

echo "✅ Upload complete"
```

### List Workspace Contents

List files in workspace directory:

```bash
# List directory
databricks workspace list /Workspace/Users/user@example.com/

# List with details (JSON format)
databricks workspace list /Workspace/Users/user@example.com/ --output json | jq -r '.objects[] | "\(.path) (\(.object_type))"'

# Recursive list
databricks workspace list /Workspace/Users/user@example.com/ --absolute --output json
```

### Delete Workspace Files

Remove files from workspace:

```bash
# Delete single file
databricks workspace delete /Workspace/Users/user@example.com/old_script.py

# Delete directory recursively
databricks workspace delete /Workspace/Users/user@example.com/old_project --recursive

# Interactive delete
read -p "Enter workspace path to delete: " WORKSPACE_PATH
read -p "Are you sure? (yes/no): " CONFIRM

if [[ "$CONFIRM" == "yes" ]]; then
    databricks workspace delete "$WORKSPACE_PATH" --recursive
    echo "✅ Deleted $WORKSPACE_PATH"
else
    echo "❌ Cancelled"
fi
```

## Troubleshooting

### CLI Syntax Errors

**Symptoms:** `Error: unknown flag: --overwrite` or `Error: accepts 1 arg(s), received 2`

**Common Mistakes:**

1. **Using "upload" instead of "import":**
   ```bash
   # ❌ WRONG - There is no "upload" command
   databricks workspace upload file.py /Workspace/path

   # ✅ CORRECT - Use "import" command
   databricks workspace import /Workspace/path --file file.py
   ```

2. **Wrong argument order:**
   ```bash
   # ❌ WRONG - Source file as positional argument
   databricks workspace import file.py /Workspace/path --language PYTHON

   # ✅ CORRECT - Source file with --file flag, target path is positional
   databricks workspace import /Workspace/path --file file.py --language PYTHON
   ```

3. **Missing --file flag:**
   ```bash
   # ❌ WRONG - Two positional arguments
   databricks workspace import file.py /Workspace/path

   # ✅ CORRECT - Use --file flag for source
   databricks workspace import /Workspace/path --file file.py
   ```

**Key Rules:**
- Command is `import`, NOT `upload`
- Target path is the ONLY positional argument (comes first or last)
- Source file MUST use `--file` flag
- Flags like `--language`, `--format`, `--overwrite` come before or after target path
- Full correct syntax:
  ```bash
  databricks workspace import [FLAGS] TARGET_PATH --file SOURCE_FILE [MORE_FLAGS]
  ```

**Example with all flags:**
```bash
databricks workspace import \
  --language PYTHON \
  --overwrite \
  /Workspace/Users/user@example.com/script.py \
  --file /path/to/local/script.py
```

### Path Already Exists

**Symptoms:** `Error: Path already exists`

**Solutions:**
1. Use `--overwrite` flag:
   ```bash
   databricks workspace import /path/to/script.py --file script.py --overwrite
   ```

2. Delete existing file first:
   ```bash
   databricks workspace delete /path/to/script.py
   databricks workspace import /path/to/script.py --file script.py
   ```

### Permission Denied

**Symptoms:** `Error: Permission denied` or `403 Forbidden`

**Solutions:**
1. Verify you have write access to the workspace path
2. Use your user directory: `/Workspace/Users/your-email@example.com/`
3. Check with workspace admin for permissions

### Invalid Path Format

**Symptoms:** `Error: Invalid path`

**Solutions:**
1. Ensure workspace paths start with `/Workspace/` or `/Repos/`
2. Don't include file extension for notebooks:
   ```bash
   # Correct
   databricks workspace import /Workspace/Users/user@example.com/notebook --file notebook.ipynb --format JUPYTER

   # Incorrect
   databricks workspace import /Workspace/Users/user@example.com/notebook.ipynb --file notebook.ipynb --format JUPYTER
   ```

### File Format Issues

**Symptoms:** Import fails with format errors

**Solutions:**
1. Specify correct format:
   - `.py` files: `--language PYTHON` or `--format SOURCE`
   - `.sql` files: `--language SQL`
   - `.ipynb` files: `--format JUPYTER`

2. Use AUTO format for automatic detection:
   ```bash
   databricks workspace import /Workspace/path --file file.txt --format AUTO
   ```

### Large Directory Upload Fails

**Symptoms:** Timeout or partial upload

**Solutions:**
1. Upload in smaller batches
2. Exclude unnecessary files:
   ```bash
   # Create temporary directory with only needed files
   rsync -av --exclude='*.pyc' --exclude='__pycache__' \
         "$LOCAL_DIR/" "$TEMP_DIR/"

   databricks workspace import-dir "$TEMP_DIR" "$WORKSPACE_PATH"
   ```

3. Check network connectivity

## Best Practices

1. **Use correct CLI syntax** - Command is `import` (not `upload`), source file needs `--file` flag
2. **Always use absolute paths** - Avoid relative paths for clarity
3. **Prompt for user input** - Don't hardcode workspace paths
4. **Use profiles for multiple workspaces** - Easier to manage
5. **Include overwrite flag for updates** - Prevents errors on re-upload
6. **Organize by user directory** - Use `/Workspace/Users/your-email/`
7. **Validate paths before operations** - Use `workspace get-status` to check
8. **Backup before large changes** - Use `export-dir` to backup first
9. **Use appropriate formats** - JUPYTER for notebooks, SOURCE for scripts
10. **Handle errors gracefully** - Check exit codes and provide feedback
11. **Use workspace mkdirs** - Create directories before uploading
12. **Remember argument order** - Target path is positional, source uses `--file`

## Integration with Other Skills

### With databricks-connect-config

After uploading code, run it using Databricks Connect:

```python
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.getOrCreate()

# Run uploaded notebook
dbutils.notebook.run("/Workspace/Users/user@example.com/my_notebook", timeout_seconds=300)
```

### With databricks-job-orchestrator

Upload code, then create a job to run it:

```bash
# Upload script
databricks workspace import /Workspace/Users/user@example.com/etl_script.py --file script.py --overwrite

# Create job that runs the script (see databricks-job-orchestrator skill)
databricks jobs create --json @job_config.json
```

## Next Steps

After uploading files:
1. Use **databricks-connect-config** skill to run code remotely
2. Use **databricks-job-orchestrator** skill to schedule execution
3. Use workspace UI to verify uploads and organize files

## Resources

### scripts/sync_helper.py

A helper script for common sync operations:

```bash
# Upload file with auto-detection
python .claude/skills/databricks-workspace-sync/scripts/sync_helper.py upload /path/to/file.py /Workspace/path

# Upload directory
python .claude/skills/databricks-workspace-sync/scripts/sync_helper.py upload-dir /path/to/dir /Workspace/path

# Download file
python .claude/skills/databricks-workspace-sync/scripts/sync_helper.py download /Workspace/path /path/to/local

# Download directory
python .claude/skills/databricks-workspace-sync/scripts/sync_helper.py download-dir /Workspace/path /path/to/local

# List workspace directory
python .claude/skills/databricks-workspace-sync/scripts/sync_helper.py list /Workspace/path
```

The helper provides:
- Automatic format detection
- Interactive prompts for missing arguments
- Progress feedback
- Error handling and validation
- Profile support
