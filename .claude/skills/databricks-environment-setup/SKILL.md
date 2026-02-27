---
name: databricks-environment-setup
description: Install and verify Databricks CLI and databricks-connect for local development. Use when setting up a new environment, troubleshooting installation issues, or checking tool versions.
---

# Databricks Environment Setup

## Overview

This skill helps you install and verify the Databricks development toolchain, including the Databricks CLI (v0.205+) and databricks-connect (v18.x) for seamless local-to-remote code execution.

## Important: Modern CLI vs Legacy CLI

**The modern Databricks CLI is a standalone Go binary, NOT a Python package.**

- ✅ **Modern CLI (correct)**: Installed via `curl`, `brew`, `winget` - this is what we use
- ❌ **Legacy CLI (wrong)**: `databricks-cli` Python package (pip install databricks-cli) - do NOT use this
- ✅ **databricks-connect**: Python package for local-to-remote execution - install via pip/uv

**Never add `databricks-cli` as a Python dependency.** The CLI is a standalone binary that must be installed separately from Python packages.

## Workflow

### 1. Check Current Installation Status

First, check what's already installed:

```bash
# Check Databricks CLI
databricks --version

# Check databricks-connect (via uv)
uv run python -c "import databricks.connect; print(databricks.connect.__version__)"

# Check Python version
python --version
```

**Expected versions (2026):**
- Databricks CLI: 0.205.0 or higher
- databricks-connect: 17.3.x or higher (pinned in pyproject.toml)
- Python: 3.12.x recommended

### 2. Install Databricks CLI

If CLI is not installed or outdated, install based on platform:

**macOS (Homebrew recommended):**
```bash
brew tap databricks/tap
brew install databricks
```

**Linux (curl):**
```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

**Windows (WinGet):**
```powershell
winget install Databricks.DatabricksCLI
```

**Alternative - Manual Download:**
Download the latest release from https://github.com/databricks/cli/releases

**Verify installation:**
```bash
databricks --version
```

### 3. Check databricks-connect

databricks-connect is managed by this project's `pyproject.toml` and installed via `uv sync`. Check if it's available:

```bash
uv run python -c "from databricks.connect import DatabricksSession; print('databricks-connect is installed')"
```

If databricks-connect is NOT installed, **ask the user** if they'd like to install it by running `uv sync`. Do not install it automatically.

**Important notes:**
- databricks-connect and pyspark are mutually exclusive
- If pyspark is installed, uninstall it first: `uv remove pyspark` or `pip uninstall pyspark`
- The pinned version in `pyproject.toml` ensures compatibility with the project

### 4. Verify Setup

Create a simple test to verify everything works:

```bash
# Test CLI connectivity (after auth - see databricks-auth-manager skill)
databricks workspace list /

# Test databricks-connect (after configuration)
python -c "from databricks.connect import DatabricksSession; print('Import successful')"
```

## Troubleshooting

### CLI Installation Issues

**Issue: Command not found**
- Ensure the CLI binary is in your PATH
- On macOS, try `brew link databricks`
- On Linux, the install script should handle PATH automatically

**Issue: Permission denied**
- On Linux/macOS, you may need sudo for system-wide installation
- Recommend user-local installation instead

### databricks-connect Issues

**Issue: Import errors**
- Ensure you're using Python 3.12.x
- Check that pyspark is not installed: `uv run pip list | grep pyspark`
- Run `uv sync` to ensure all dependencies are installed

**Issue: Version mismatch**
- The version is pinned in `pyproject.toml` — update it there and run `uv sync`

**Issue: Virtual environment problems**
- Recreate with: `rm -rf .venv && uv sync`

## Next Steps

After installation:
1. Use **databricks-auth-manager** skill to configure authentication
2. Use **databricks-connect-config** skill to set up remote execution
3. Start writing code that runs locally and on Databricks!

## Resources

### scripts/check_environment.py

A diagnostic script to check your environment:

```python
# Run this script to verify your setup
python .claude/skills/databricks-environment-setup/scripts/check_environment.py
```

This will check:
- Databricks CLI installation and version
- databricks-connect installation and version
- Python version compatibility
- Virtual environment status
- Common issues and recommendations
