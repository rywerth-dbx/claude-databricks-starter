# Databricks + Claude Code Starter

A comprehensive starter project for using Claude Code with Databricks, featuring custom skills for local development with remote execution via databricks-connect.

## Overview

This project provides a complete development environment for writing Databricks code locally that executes remotely without modification. It includes five custom Claude Code skills that guide you through setup, authentication, configuration, and deployment.

## Features

- ✅ **Local-to-Remote Execution**: Write and test code locally that runs seamlessly on Databricks
- ✅ **No Hardcoded Values**: All skills prompt for workspace URLs, cluster IDs, and paths
- ✅ **Multi-Workspace Support**: Manage multiple Databricks workspaces with profiles
- ✅ **CLI Integration**: Full Databricks CLI support with OAuth authentication
- ✅ **Job Orchestration**: Create, run, and monitor Databricks jobs from your terminal
- ✅ **Workspace Sync**: Upload and download code, notebooks, and files

## Prerequisites

- Python 3.10+ (3.12 recommended)
- macOS, Linux, or Windows with WSL
- A Databricks workspace

## Quick Start

### 1. Set Up Your Environment

```bash
# Use the environment setup skill
/databricks-environment-setup
```

This will guide you through:
- Installing Databricks CLI
- Installing databricks-connect
- Verifying your Python environment
- Checking for common issues

### 2. Authenticate with Databricks

```bash
# Use the authentication manager skill
/databricks-auth-manager
```

This will help you:
- Configure OAuth authentication
- Set up workspace profiles
- Test connectivity

### 3. Configure databricks-connect

```bash
# Use the connect config skill
/databricks-connect-config
```

This will show you how to:
- Initialize SparkSession
- Connect to clusters or serverless compute
- Test your connection

### 4. Start Coding!

Create a Python file and run it locally:

```python
# my_analysis.py
from databricks.connect import DatabricksSession

# Initialize session (executes remotely!)
spark = DatabricksSession.builder.getOrCreate()

# Your code runs on Databricks, not locally
df = spark.range(1000)
result = df.filter("id > 500").count()
print(f"Count: {result}")

spark.stop()
```

```bash
# Run locally - executes on Databricks!
python my_analysis.py
```

## Available Skills

### 1. databricks-environment-setup

Install and verify the Databricks development toolchain.

**Use when:**
- Setting up a new development environment
- Troubleshooting installation issues
- Checking tool versions

**Includes:**
- `scripts/check_environment.py` - Diagnostic tool for your environment

### 2. databricks-auth-manager

Configure authentication using OAuth with profiles.

**Use when:**
- First-time authentication setup
- Managing multiple workspaces
- Troubleshooting auth issues

**Includes:**
- `scripts/auth_helper.py` - Check authentication status and profiles

### 3. databricks-connect-config

Set up databricks-connect for local-to-remote execution.

**Use when:**
- Initializing SparkSession
- Configuring cluster connections
- Testing databricks-connect

**Includes:**
- `scripts/test_connection.py` - Comprehensive connection test

### 4. databricks-workspace-sync

Upload and download files to/from Databricks workspace.

**Use when:**
- Deploying code to workspace
- Backing up notebooks
- Syncing project files

**Includes:**
- `scripts/sync_helper.py` - Interactive upload/download tool

### 5. databricks-job-orchestrator

Create, run, and monitor Databricks jobs.

**Use when:**
- Creating production jobs
- Running notebooks or Python files as jobs
- Monitoring job execution

**Includes:**
- `scripts/job_helper.py` - Interactive job management tool

## Typical Workflow

1. **Setup** (once)
   ```bash
   /databricks-environment-setup
   /databricks-auth-manager
   /databricks-connect-config
   ```

2. **Develop** (iterative)
   - Write code locally with your favorite IDE
   - Test with databricks-connect (executes remotely)
   - No code changes needed between local and remote

3. **Deploy** (when ready)
   ```bash
   # Upload your code
   /databricks-workspace-sync

   # Create a job
   /databricks-job-orchestrator
   ```

## Example: End-to-End Workflow

```bash
# 1. Check environment
python .claude/skills/databricks-environment-setup/scripts/check_environment.py

# 2. Authenticate
databricks auth login --host https://your-workspace.cloud.databricks.com

# 3. Test connection
python .claude/skills/databricks-connect-config/scripts/test_connection.py

# 4. Write your code
cat > my_job.py << 'EOF'
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.getOrCreate()
df = spark.sql("SELECT * FROM my_table LIMIT 10")
df.show()
spark.stop()
EOF

# 5. Test locally (runs on Databricks)
python my_job.py

# 6. Upload to workspace
python .claude/skills/databricks-workspace-sync/scripts/sync_helper.py \
  upload my_job.py /Users/me/my_job.py

# 7. Create and run a job
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py \
  create --name "My Job" --file /Users/me/my_job.py
```

## Project Structure

```
.
├── .claude/
│   └── skills/                              # Custom Claude Code skills
│       ├── databricks-environment-setup/    # Install & verify tools
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── check_environment.py
│       ├── databricks-auth-manager/         # OAuth authentication
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── auth_helper.py
│       ├── databricks-connect-config/       # Configure remote execution
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── test_connection.py
│       ├── databricks-workspace-sync/       # Upload/download files
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── sync_helper.py
│       └── databricks-job-orchestrator/     # Create & run jobs
│           ├── SKILL.md
│           └── scripts/
│               └── job_helper.py
├── CLAUDE.md                                # Project instructions for Claude Code
└── README.md                                # This file
```

## Key Design Principles

1. **No Hardcoded Values**: All skills prompt for workspace URLs, cluster IDs, and paths to ensure they work in any environment

2. **Profile-Based Authentication**: Support multiple workspaces through Databricks profiles

3. **Simple and Direct**: Uses straightforward `DatabricksSession.builder.getOrCreate()` without unnecessary complexity

4. **Flexible Structure**: No enforced directory structure - organize your code however you want

5. **Interactive Helpers**: All scripts provide interactive prompts when run without arguments

## Extending This Project

This starter is intentionally minimal. You can extend it by:

- Adding your own custom skills in `.claude/skills/`
- Creating project-specific configuration files
- Adding CI/CD pipelines
- Creating shared utility modules
- Adding testing frameworks

## Troubleshooting

### Common Issues

**Issue: Command not found**
- Run `/databricks-environment-setup` to install CLI

**Issue: Authentication failed**
- Run `/databricks-auth-manager` to configure OAuth

**Issue: Connection error**
- Run `python .claude/skills/databricks-connect-config/scripts/test_connection.py`

**Issue: Version mismatch**
- Match databricks-connect version to your cluster's Databricks Runtime
- `pip install "databricks-connect==X.Y.*"` where X.Y matches your runtime

### Getting Help

1. Check skill documentation: Each skill's `SKILL.md` has detailed troubleshooting
2. Run diagnostic scripts in `scripts/` directories
3. Check the [Databricks CLI documentation](https://docs.databricks.com/dev-tools/cli/)
4. Check the [databricks-connect documentation](https://docs.databricks.com/dev-tools/databricks-connect/)

## Resources

- [Databricks Connect Documentation](https://docs.databricks.com/dev-tools/databricks-connect/)
- [Databricks CLI Documentation](https://docs.databricks.com/dev-tools/cli/)
- [Claude Code Documentation](https://claude.ai/code)
- [Databricks Developer Tools](https://docs.databricks.com/dev-tools/)

## License

This project is provided as-is for use as a starting point. Modify and extend as needed for your use case.

## Contributing

This is a starter project designed to be forked and customized. Feel free to:
- Add new skills for your specific use cases
- Improve existing skills
- Share your extensions with others

---

**Ready to get started?** Run `/databricks-environment-setup` in Claude Code to begin!
