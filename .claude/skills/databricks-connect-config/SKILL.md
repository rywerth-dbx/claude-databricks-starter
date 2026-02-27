---
name: databricks-connect-config
description: Configure Databricks Connect for seamless local-to-remote code execution. Use when setting up DatabricksSession, writing code for databricks, or switching between serverless and cluster-based execution.
---

# Databricks Connect Configuration

## Overview

This skill helps you configure Databricks Connect to execute Spark code locally that runs remotely on Databricks clusters or serverless compute. The key principle is to **always use `DatabricksSession.builder.getOrCreate()` without hardcoding any configuration** - all settings are managed via environment variables.

## Core Principle: Environment Variable Configuration

**CRITICAL:** NEVER hardcode profile, cluster ID, or serverless configuration in your code. Always use:

```python
from databricks.connect import DatabricksSession

# This is the ONLY way to create a session
spark = DatabricksSession.builder.getOrCreate()
```

All configuration happens via environment variables, allowing the same code to run:
- **Locally** with Databricks Connect (using environment variables)
- **In Databricks workspace** (automatically authenticated, no environment variables needed)

## Prerequisites: Required Environment Variables

**CRITICAL:** Before running ANY Databricks Connect code locally, you MUST set these environment variables:

### Required Variables

1. **DATABRICKS_CONFIG_PROFILE** (Recommended) - Your Databricks CLI profile name
   - If not set, will use the **DEFAULT** profile
   - Find available profiles: `databricks auth profiles`
   - Created during authentication: `/databricks-auth-manager`
   - **Best practice:** Always set this explicitly to avoid confusion about which workspace you're using

2. **Compute Configuration** (REQUIRED) - Choose ONE:
   - **DATABRICKS_SERVERLESS_COMPUTE_ID=auto** (Recommended) - Use serverless compute
   - **DATABRICKS_CLUSTER_ID=<cluster-id>** - Use specific cluster

### Quick Check

Verify your environment variables are set:

```bash
# Check if variables are set
echo $DATABRICKS_CONFIG_PROFILE  # Will use DEFAULT if not set
echo $DATABRICKS_SERVERLESS_COMPUTE_ID  # Must be set
# OR
echo $DATABRICKS_CLUSTER_ID  # Must be set

# If not set, load from .env
source .env

# Verify which workspace you'll connect to
databricks auth profiles
```

### Confirming Your Workspace

Before running code, **always verify which workspace you'll be connecting to:**

```bash
# List all profiles and their workspaces
databricks auth profiles

# If using DEFAULT profile, check which workspace it points to
grep -A 2 "^\[DEFAULT\]" ~/.databrickscfg

# Test connection and see workspace URL
python .claude/skills/databricks-connect-config/scripts/test_connection.py
```

**If compute is not set, your code will fail with:**
```
Error: Cluster id or serverless are required but were not specified
```

## CRITICAL: Handling Connection Issues (For Claude)

**NEVER modify Python code to fix connection issues.** Connection problems are ALWAYS solved by configuring the environment, never by changing code.

### The Golden Rule:

```python
# ✅ ALWAYS write code like this - NO exceptions
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
```

**DO NOT:**
- Add `os.environ` logic to set variables in code
- Add `try/except` blocks for auth errors
- Modify `DatabricksSession.builder` with any parameters
- Add environment variable checks or fallbacks

### When Connection Fails - Follow This Workflow:

1. **Check available profiles**:
   ```bash
   cat ~/.databrickscfg
   ```

2. **List profiles with workspace URLs**:
   ```bash
   grep -E "^\[|^host" ~/.databrickscfg
   ```

3. **Ask the user which workspace** they want to connect to

4. **Set DATABRICKS_CONFIG_PROFILE**:
   ```bash
   export DATABRICKS_CONFIG_PROFILE=<chosen-profile>
   ```

5. **Run the script unchanged**

### Example Claude Workflow:

```
[Connection error occurs]

Claude: I see a connection error. Let me check your available Databricks profiles.
        [runs: cat ~/.databrickscfg]

Claude: You have these workspaces:
        - fe-vm-ryan-werth-workspace: https://fevm-ryan-werth-workspace.cloud.databricks.com
        - e2-demo-field-eng: https://e2-demo-field-eng.cloud.databricks.com
        - logfood: https://adb-2548836972759138.18.azuredatabricks.net

        Which workspace would you like to connect to?

User: Use fe-vm-ryan-werth-workspace

Claude: Setting profile and running script...
        [runs: export DATABRICKS_CONFIG_PROFILE=fe-vm-ryan-werth-workspace && python script.py]
```

### Why This Matters:

- **Portability**: Same code runs locally, in notebooks, and in jobs
- **Simplicity**: No conditional logic or environment detection needed
- **Best Practice**: Configuration belongs in environment, not code
- **Maintainability**: One way to do it means less confusion

## When DATABRICKS_CONFIG_PROFILE is Not Set

**For Claude:** If `DATABRICKS_CONFIG_PROFILE` is not set, follow this workflow:

1. **Inform the user** that it will default to the DEFAULT profile
2. **Check which workspace** the DEFAULT profile points to:
   ```bash
   databricks auth profiles
   # or
   grep -A 2 "^\[DEFAULT\]" ~/.databrickscfg | grep "host"
   ```
3. **Ask the user** to confirm they want to use that workspace, or help them set a different profile:
   - **Option A:** User confirms DEFAULT is correct → proceed
   - **Option B:** User wants a different workspace → help them set `DATABRICKS_CONFIG_PROFILE`:
     ```bash
     # List available profiles
     databricks auth profiles

     # Set the desired profile
     export DATABRICKS_CONFIG_PROFILE=<chosen-profile>

     # Update .env file if using one
     echo "export DATABRICKS_CONFIG_PROFILE=<chosen-profile>" >> .env
     ```

**Example conversation:**
```
Claude: I notice DATABRICKS_CONFIG_PROFILE is not set. This means we'll use
        the DEFAULT profile, which points to: https://workspace.cloud.databricks.com

        Is this the workspace you want to use? If not, I can help you set a
        different profile. Available profiles:
        - DEFAULT (https://workspace.cloud.databricks.com)
        - dev-workspace (https://dev.cloud.databricks.com)
        - prod-workspace (https://prod.cloud.databricks.com)

User: Let's use dev-workspace

Claude: Great! Setting DATABRICKS_CONFIG_PROFILE to dev-workspace...
        [runs: export DATABRICKS_CONFIG_PROFILE=dev-workspace]
```

## Configuration Options

### Option 1: Serverless Compute (Recommended)

For local development using serverless compute:

```bash
# Set these environment variables before running your script
export DATABRICKS_CONFIG_PROFILE=<your-profile-name>
export DATABRICKS_SERVERLESS_COMPUTE_ID=auto
```

**Benefits:**
- No cluster management required
- Instant startup
- Auto-scaling
- Pay only for what you use

**Limitations:**
- `.cache()` and `.persist()` are NOT supported on serverless compute
- If your code needs caching, use a cluster instead

**Example:**
```bash
export DATABRICKS_CONFIG_PROFILE=fe-vm-ryan-werth-workspace
export DATABRICKS_SERVERLESS_COMPUTE_ID=auto
python my_script.py
```

### Option 2: Specific Cluster

For local development using a specific cluster:

```bash
# Set these environment variables before running your script
export DATABRICKS_CONFIG_PROFILE=<your-profile-name>
export DATABRICKS_CLUSTER_ID=<cluster-id>
```

**When to use clusters:**
- Need specific Databricks Runtime version
- Require custom libraries or init scripts
- Need specific instance types
- Working with Unity Catalog that requires cluster configuration

**Finding cluster IDs:**
```bash
# List all clusters
databricks clusters list --output json

# List running clusters only
databricks clusters list --output json | jq '.clusters[] | select(.state == "RUNNING") | {cluster_id, cluster_name}'
```

**Example:**
```bash
export DATABRICKS_CONFIG_PROFILE=my-workspace
export DATABRICKS_CLUSTER_ID=1234-567890-abcdef12
python my_script.py
```

## Recommended Setup: .env File

Create a `.env` file in your project directory for easy configuration:

```bash
# .env file for local development
# When running in Databricks workspace, these are not needed

# Option 1: Use serverless (recommended)
export DATABRICKS_CONFIG_PROFILE=fe-vm-ryan-werth-workspace
export DATABRICKS_SERVERLESS_COMPUTE_ID=auto

# Option 2: Use specific cluster (uncomment to use)
# export DATABRICKS_CONFIG_PROFILE=fe-vm-ryan-werth-workspace
# export DATABRICKS_CLUSTER_ID=<your-cluster-id>
```

**Usage:**
```bash
# Load environment variables
source .env

# Run your script
python my_script.py
```

## Complete Example

**PySpark Script (my_script.py):**
```python
"""
Sample PySpark script that works in both local and Databricks environments.
Configuration is handled via environment variables (local) or automatic (Databricks).
"""

from databricks.connect import DatabricksSession
from pyspark.sql import functions as F

def main():
    # Create session - configured via environment variables when running locally
    print("Creating Databricks session...")
    spark = DatabricksSession.builder.getOrCreate()

    print(f"Connected to Databricks - Spark version: {spark.version}")

    # Your Spark code here
    df = spark.createDataFrame([
        ("Alice", 34, "Engineering"),
        ("Bob", 45, "Sales"),
    ], ["name", "age", "department"])

    df.show()

    print("✓ Job completed successfully!")

if __name__ == "__main__":
    main()
```

**Running Locally:**
```bash
# Set environment variables
export DATABRICKS_CONFIG_PROFILE=fe-vm-ryan-werth-workspace
export DATABRICKS_SERVERLESS_COMPUTE_ID=auto

# Run the script
python my_script.py
```

**Running in Databricks Workspace:**
Upload the script to Databricks and run it as a notebook or job - no environment variables needed!

## Verifying Your Setup

### Check Authentication

```bash
# List available profiles
databricks auth profiles

# Verify profile is valid (check the "Valid" column)
databricks auth profiles | grep <your-profile-name>

# Test authentication
databricks workspace list / --profile <your-profile-name>
```

### Test Connection

```python
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.getOrCreate()

# Simple test
print(f"Spark version: {spark.version}")
print(f"Row count test: {spark.range(100).count()}")

# Check if using serverless or cluster
cluster_id = spark.conf.get('spark.databricks.clusterUsageTags.clusterId', 'serverless')
print(f"Compute type: {cluster_id}")
```

## Common Operations

### Read and Write Data

```python
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.getOrCreate()

# Read from Unity Catalog
df = spark.read.table("main.default.my_table")

# Read from DBFS
df = spark.read.parquet("dbfs:/mnt/data/file.parquet")

# Write to Unity Catalog
df.write.mode("overwrite").saveAsTable("main.default.output_table")

# Write to DBFS
df.write.mode("overwrite").parquet("dbfs:/mnt/data/output/")
```

### Working with DataFrames

```python
from databricks.connect import DatabricksSession
from pyspark.sql import functions as F

spark = DatabricksSession.builder.getOrCreate()

# Create DataFrame
df = spark.createDataFrame([
    ("Alice", 34),
    ("Bob", 45),
], ["name", "age"])

# Transform
df_transformed = df.withColumn("age_group",
    F.when(F.col("age") < 40, "Young").otherwise("Senior")
)

# Aggregate
df_agg = df.groupBy("age_group").count()

df_agg.show()
```

## Troubleshooting

### Error: "Cluster id or serverless are required but were not specified"

**Cause:** Environment variables are not set

**Solution:**
```bash
# For serverless
export DATABRICKS_CONFIG_PROFILE=<your-profile>
export DATABRICKS_SERVERLESS_COMPUTE_ID=auto

# OR for cluster
export DATABRICKS_CONFIG_PROFILE=<your-profile>
export DATABRICKS_CLUSTER_ID=<cluster-id>
```

### Connection Refused or Authentication Errors

**Symptoms:** `ConnectionRefusedError` or authentication failures

**Solutions:**
1. Verify authentication:
   ```bash
   databricks auth profiles
   databricks workspace list / --profile <your-profile>
   ```

2. Re-authenticate if needed:
   ```bash
   databricks auth login --host <workspace-url> --profile <your-profile>
   ```

### Cluster Not Found

**Symptoms:** `Cluster not found` or `Invalid cluster ID`

**Solutions:**
1. List available clusters:
   ```bash
   databricks clusters list --profile <your-profile>
   ```

2. Ensure cluster is running:
   ```bash
   databricks clusters get --cluster-id <cluster-id> --profile <your-profile>
   ```

3. Start cluster if stopped:
   ```bash
   databricks clusters start --cluster-id <cluster-id> --profile <your-profile>
   ```

### Module Import Errors

**Symptoms:** `ModuleNotFoundError: No module named 'databricks.connect'`

**Solutions:**
```bash
# Check if installed
pip show databricks-connect

# Install if missing
pip install databricks-connect

# Verify installation
pip list | grep databricks
```

### Version Mismatch

**Symptoms:** Version compatibility warnings or runtime errors

**Solutions:**
Match databricks-connect version to cluster runtime:
```bash
# For DBR 17.3 LTS
pip install "databricks-connect==17.3.*"

# For DBR 18.0
pip install "databricks-connect==18.0.*"
```

Check cluster runtime version in workspace UI before installing.

### Serverless Not Available

**Symptoms:** Serverless compute not available or disabled

**Solutions:**
1. Ensure workspace has serverless enabled (Premium or Enterprise tier)
2. Switch to using a specific cluster:
   ```bash
   export DATABRICKS_CONFIG_PROFILE=<your-profile>
   export DATABRICKS_CLUSTER_ID=<cluster-id>
   ```

## Best Practices

1. **NEVER modify code to fix connection issues** - Connection problems are ALWAYS solved by setting environment variables, never by changing code
2. **NEVER hardcode configuration in code** - Always use `DatabricksSession.builder.getOrCreate()`
3. **When connection fails** - Check `~/.databrickscfg`, ask user which workspace, set `DATABRICKS_CONFIG_PROFILE`
4. **Use environment variables for local development** - Set `DATABRICKS_CONFIG_PROFILE` + (`DATABRICKS_SERVERLESS_COMPUTE_ID` or `DATABRICKS_CLUSTER_ID`)
5. **Create a .env file** - Store environment variables in a `.env` file for easy management
6. **Add .env to .gitignore** - Never commit environment configuration to version control
7. **Default to serverless** - Simpler and more cost-effective for most workloads (but note: no `.cache()` or `.persist()` support)
8. **Test connection after setup** - Use `spark.range(10).count()` to verify
9. **Match runtime versions** - Keep databricks-connect version aligned with cluster runtime
10. **Use virtual environments** - Isolate dependencies per project
11. **Write portable code** - Same code should run locally and in Databricks workspace

## Summary

### Always Use This Pattern:

```python
# ✅ CORRECT - Configuration via environment variables
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
```

### Never Use These Patterns:

```python
# ❌ WRONG - Hardcoded profile
spark = DatabricksSession.builder.profile("dev").getOrCreate()

# ❌ WRONG - Hardcoded cluster
spark = DatabricksSession.builder.clusterId("1234-567890").getOrCreate()

# ❌ WRONG - Hardcoded serverless
spark = DatabricksSession.builder.serverless(True).getOrCreate()
```

### Environment Variables:

**Serverless (Recommended):**
```bash
export DATABRICKS_CONFIG_PROFILE=<your-profile>
export DATABRICKS_SERVERLESS_COMPUTE_ID=auto
```

**Cluster:**
```bash
export DATABRICKS_CONFIG_PROFILE=<your-profile>
export DATABRICKS_CLUSTER_ID=<cluster-id>
```

## Next Steps

After configuration:
1. Use **databricks-workspace-sync** skill to upload code and notebooks
2. Use **databricks-job-orchestrator** skill to create and schedule jobs
3. Start developing locally with full Databricks capabilities
4. Write portable code that works seamlessly in both local and workspace environments
