---
name: databricks-auth-manager
description: Configure Databricks authentication using OAuth U2M with profiles. Use when setting up authentication, managing multiple workspaces, or troubleshooting auth issues.
---

# Databricks Authentication Manager

## Overview

This skill helps you set up and manage Databricks authentication using OAuth user-to-machine (U2M) authentication with configuration profiles. Supports multiple workspaces without hardcoded credentials.

## Workflow

### 1. Interactive OAuth Authentication (Recommended)

The simplest way to authenticate with OAuth:

```bash
# Authenticate with your workspace
databricks auth login --host <WORKSPACE_URL>
```

**Example:**
```bash
databricks auth login --host https://my-workspace.cloud.databricks.com
```

This will:
1. Open your browser for OAuth authentication
2. Create/update `~/.databrickscfg` with a DEFAULT profile
3. Cache tokens in `~/.databricks/token-cache.json`
4. Automatically refresh tokens (valid for 1 hour each)

### 2. Using Named Profiles

For multiple workspaces, use named profiles:

```bash
# Create a profile for dev workspace
databricks auth login --host https://dev-workspace.cloud.databricks.com --profile dev

# Create a profile for prod workspace
databricks auth login --host https://prod-workspace.cloud.databricks.com --profile prod
```

**Using a specific profile:**
```bash
# List workspaces using dev profile
databricks workspace list / --profile dev

# List workspaces using prod profile
databricks workspace list / --profile prod
```

**Set default profile with environment variable:**
```bash
export DATABRICKS_CONFIG_PROFILE=dev
databricks workspace list /
```

### 3. Verify Authentication

Test your authentication:

```bash
# Check current authentication status
databricks auth describe

# List available profiles
databricks auth profiles

# Test connectivity
databricks workspace list /
```

### 4. Configuration File Structure

Your `~/.databrickscfg` file will look like this:

```ini
[DEFAULT]
host = https://my-workspace.cloud.databricks.com
auth_type = oauth

[dev]
host = https://dev-workspace.cloud.databricks.com
auth_type = oauth

[prod]
host = https://prod-workspace.cloud.databricks.com
auth_type = oauth
```

**Important:** Do NOT commit `.databrickscfg` to version control. Add it to `.gitignore`.

## Alternative Authentication Methods

### Environment Variables

For CI/CD or scripting:

```bash
# Using OAuth token
export DATABRICKS_HOST="https://my-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="<your-token>"

# Or using personal access token (PAT) - not recommended
export DATABRICKS_HOST="https://my-workspace.cloud.databricks.com"
export DATABRICKS_PAT="<your-pat>"
```

### Manual Profile Configuration

You can manually edit `~/.databrickscfg`:

```ini
[my-profile]
host = https://my-workspace.cloud.databricks.com
auth_type = oauth
```

Then authenticate:
```bash
databricks auth login --profile my-profile
```

## Common Operations

### Prompt User for Workspace

When writing scripts or skills, always prompt for the workspace URL:

```bash
# Get workspace URL from user
read -p "Enter Databricks workspace URL: " WORKSPACE_URL

# Authenticate
databricks auth login --host "$WORKSPACE_URL"
```

### Prompt for Profile Selection

```bash
# List available profiles
databricks auth profiles

# Let user choose
read -p "Enter profile name (or press Enter for DEFAULT): " PROFILE_NAME
PROFILE_NAME=${PROFILE_NAME:-DEFAULT}

# Use selected profile
databricks workspace list / --profile "$PROFILE_NAME"
```

### Check if Authenticated

```python
#!/usr/bin/env python3
import subprocess
import sys

def check_auth(profile=None):
    """Check if authenticated with Databricks."""
    cmd = ["databricks", "workspace", "list", "/", "--output", "json"]
    if profile:
        cmd.extend(["--profile", profile])

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        return False

if __name__ == "__main__":
    profile = sys.argv[1] if len(sys.argv) > 1 else None
    if check_auth(profile):
        print(f"✅ Authenticated successfully")
        sys.exit(0)
    else:
        print(f"❌ Not authenticated")
        print(f"Run: databricks auth login --host <workspace-url>")
        sys.exit(1)
```

## Troubleshooting

### Token Expired or Invalid

```bash
# Re-authenticate
databricks auth login --host <WORKSPACE_URL> --profile <PROFILE_NAME>
```

### Multiple Profiles Conflict

```bash
# Explicitly specify profile
databricks workspace list / --profile my-profile

# Or use environment variable
export DATABRICKS_CONFIG_PROFILE=my-profile
```

### Can't Access Workspace

- Verify workspace URL is correct (should start with `https://`)
- Check you have access to the workspace in the browser
- Ensure your user has appropriate permissions
- Try clearing token cache: `rm -rf ~/.databricks/token-cache.json`

### Browser Not Opening

If the OAuth browser window doesn't open:
1. Copy the URL from the terminal
2. Paste it in your browser manually
3. Complete authentication
4. Return to terminal

## Security Best Practices

1. **Never hardcode credentials** - Always use profiles or environment variables
2. **Use OAuth U2M** - Preferred over personal access tokens (PATs)
3. **Add to .gitignore:**
   ```
   .databrickscfg
   .databricks/
   ```
4. **Use named profiles** - Easier to manage multiple workspaces
5. **Rotate tokens regularly** - Tokens auto-expire after 1 hour
6. **Use service principals for automation** - For CI/CD and production systems

## Integration with databricks-connect

After authentication, databricks-connect will use the same credentials:

```python
from databricks.connect import DatabricksSession

# Uses DEFAULT profile
spark = DatabricksSession.builder.getOrCreate()

# Use specific profile
spark = DatabricksSession.builder.profile("dev").getOrCreate()
```

## Next Steps

After authentication:
1. Use **databricks-connect-config** skill to configure remote execution
2. Use **databricks-workspace-sync** skill to upload code
3. Use **databricks-job-orchestrator** skill to create and run jobs

## Resources

### scripts/auth_helper.py

A helper script for authentication checks:

```bash
# Check if authenticated
python .claude/skills/databricks-auth-manager/scripts/auth_helper.py

# Check specific profile
python .claude/skills/databricks-auth-manager/scripts/auth_helper.py dev
```
