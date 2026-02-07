# Databricks + Claude Code Starter

An extremely simple setup for working with Claude and Databricks locally. Write code, manage your workspace, and query data—all from your local machine.


## Overview

This starter kit provides everything you need to develop Databricks applications locally with Claude Code. It's built around three core capabilities:

### 1. 📝 Writing Code - Databricks Connect

Write code locally that runs seamlessly on Databricks without any modifications. The same files work both locally and when deployed to your workspace.

**Skill:** `databricks-connect-config`
- Teaches Claude how to use Databricks Connect
- Configure SparkSession for local-to-remote execution
- Connect to clusters or serverless compute

### 2. 🔧 Workspace Operations - Databricks CLI

Interact with your Databricks workspace using the [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/commands), which lets you do almost anything—create jobs, upload files, manage clusters, and more.

**Skills:**
- `databricks-auth-manager` - Configure OAuth authentication with profiles
- `databricks-environment-setup` - Install and verify Databricks CLI and tools
- `databricks-job-orchestrator` - Create, run, and monitor jobs
- `databricks-workspace-sync` - Upload and download files to/from workspace

### 3. 🔍 Querying Data - Databricks DBSQL MCP Server

Run SQL queries against your workspace using the [Databricks DBSQL MCP Server](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp), giving Claude direct access to query your data.

**Configuration:** `.mcp.json`
- Configured MCP server for SQL queries
- Uses workspace URL and authentication token

## Quick Start

### Prerequisites

- Python 3.10+ (3.12 recommended)
- A Databricks workspace
- macOS, Linux, or Windows with WSL

### 0. Initial Setup

First, get the repository and configure your environment:

```bash
# Clone or download this repository
git clone <repository-url>
cd ClaudeCodeDatabricks

# Copy the environment template
cp .env.example .env
```

Edit `.env` and fill in:

1. **DATABRICKS_WORKSPACE_URL** - Your workspace URL (e.g., `https://your-workspace.cloud.databricks.com`)

2. **DATABRICKS_TOKEN** - Your Personal Access Token
   - Generate one from your workspace: User Settings → Developer → Access Tokens
   - [Databricks PAT Documentation](https://docs.databricks.com/en/dev-tools/auth/pat.html)

3. **DATABRICKS_CONFIG_PROFILE** (Optional) - Your Databricks CLI profile name
   - Used by Databricks Connect to know which workspace to connect to
   - If you don't know it yet, no worries—you'll set this up in Step 2
   - You can find profiles in `~/.databrickscfg` or leave as-is for now

Then, navigate to the directory and start Claude Code:

```bash
# Load environment variables
source .env

# Start Claude Code in this directory
claude
```

### 1. Set Up Environment

Install and verify the tools:

```bash
/databricks-environment-setup
```

### 2. Authenticate

Configure OAuth authentication for your workspace:

```bash
/databricks-auth-manager
```

This creates a profile in `~/.databrickscfg`. After this step, you can update `DATABRICKS_CONFIG_PROFILE` in your `.env` file if needed.

### 3. Configure Databricks Connect

Set up local-to-remote execution:

```bash
/databricks-connect-config
```

### 4. Start Working!

Now you can:
- Write Python files that execute on Databricks
- Ask Claude to query your data
- Upload files and create jobs
- Manage your workspace from the command line

### 5. Extend with Custom Skills and CLAUDE.MD

#### CLAUDE.MD - Project Instructions
The `CLAUDE.md` file in this repository is currently empty and ready for you to use. This file provides persistent instructions that Claude will read in every conversation for this project. Use it to:

- Define project-specific conventions and patterns
- Add shortcuts and preferences for how you work
- Document company or user specific configurations for your workspace
- Store instructions that apply across all conversations in this directory

Start by adding instructions about workspace and catalog names.

#### Creating Custom Skills
Want to work with Lakebase, Databricks Apps, or other features not covered by the included skills?

1. **Direct Claude to documentation** - Share Databricks docs for the feature you want to use
2. **Work with Claude to try it** - Experiment and test the feature together
3. **Create a skill for it** - Use the included [skill-creator](/.claude/skills/skill-creator/) skill: simply tell claude to take what it's learned and use it's skill-creator skill to create a skill

Each skill you create becomes part of your toolkit and can be used across projects.


## Project Structure

```
.
├── .claude/
│   └── skills/                              # Custom Claude Code skills
│       ├── databricks-environment-setup/    # Install & verify CLI/tools
│       ├── databricks-auth-manager/         # OAuth authentication setup
│       ├── databricks-connect-config/       # Local-to-remote execution
│       ├── databricks-workspace-sync/       # Upload/download files
│       └── databricks-job-orchestrator/     # Job management
├── .mcp.json                                # MCP server configuration (DBSQL)
├── .env.example                             # Environment variables template
└── README.md                                # This file
```


## Troubleshooting

### CLI Not Found
Run `/databricks-environment-setup` to install

### Authentication Failed
Run `/databricks-auth-manager` to configure OAuth

### Connection Error
Run `/databricks-connect-config` to test connection

### MCP Server Issues
- Verify `.env` is sourced: `source .env`
- Check variables are set: `echo $DATABRICKS_WORKSPACE_URL`
- Verify token is valid: `databricks auth token`

## Resources

- [Databricks Connect](https://docs.databricks.com/dev-tools/databricks-connect/)
- [Databricks CLI Commands](https://docs.databricks.com/aws/en/dev-tools/cli/commands)
- [Databricks DBSQL MCP Server](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)
- [Claude Code](https://claude.ai/code)

## License

This project is provided as-is as a starting point. Modify and extend as needed.

---

**Ready to start?** Run `/databricks-environment-setup` in Claude Code!
