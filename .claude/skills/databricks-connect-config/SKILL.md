---
name: databricks-connect-config
description: Configure Databricks Connect for seamless local-to-remote code execution. Use when setting up DatabricksSession, connecting to clusters, or switching between serverless and cluster-based execution.
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

1. **NEVER hardcode configuration in code** - Always use `DatabricksSession.builder.getOrCreate()`
2. **Use environment variables for local development** - Set `DATABRICKS_CONFIG_PROFILE` + (`DATABRICKS_SERVERLESS_COMPUTE_ID` or `DATABRICKS_CLUSTER_ID`)
3. **Create a .env file** - Store environment variables in a `.env` file for easy management
4. **Add .env to .gitignore** - Never commit environment configuration to version control
5. **Default to serverless** - Simpler and more cost-effective for most workloads
6. **Test connection after setup** - Use `spark.range(10).count()` to verify
7. **Match runtime versions** - Keep databricks-connect version aligned with cluster runtime
8. **Use virtual environments** - Isolate dependencies per project
9. **Write portable code** - Same code should run locally and in Databricks workspace

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
