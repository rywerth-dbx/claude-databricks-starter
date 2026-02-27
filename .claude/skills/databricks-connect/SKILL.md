---
name: databricks-connect
description: Guide for writing code with Databricks Connect and debugging connection issues. Use when writing PySpark code, using DatabricksSession, choosing serverless vs cluster compute, or troubleshooting connection errors.
---

# Databricks Connect

## Core Principle

**NEVER hardcode configuration in code.** All settings are managed via environment variables.

```python
from databricks.connect import DatabricksSession

# This is the ONLY way to create a session
spark = DatabricksSession.builder.getOrCreate()
```

This same code works both locally (via env vars) and in Databricks workspace (auto-authenticated).

**DO NOT** add `os.environ` logic, `try/except` for auth, `.profile()`, `.clusterId()`, or `.serverless()` to code.

## Environment Variables

Set these in your `.env` file and load with `source .env`.

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

Find cluster IDs with: `databricks clusters list --output json`

## Serverless vs Cluster

| | Serverless | Cluster |
|---|---|---|
| Startup | Instant | Minutes (if stopped) |
| Cost | Pay per use | Running cost |
| `.cache()` / `.persist()` | NOT supported | Supported |
| Custom libraries | No | Yes (init scripts) |
| Best for | Most development | Caching, custom envs |

Default to serverless unless you need caching or custom libraries.

## Code Examples

### Read and Write Data

```python
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.getOrCreate()

# Read from Unity Catalog
df = spark.read.table("catalog.schema.my_table")

# Write to Unity Catalog
df.write.mode("overwrite").saveAsTable("catalog.schema.output_table")

# Read/write parquet
df = spark.read.parquet("dbfs:/mnt/data/file.parquet")
df.write.mode("overwrite").parquet("dbfs:/mnt/data/output/")
```

### DataFrame Operations

```python
from databricks.connect import DatabricksSession
from pyspark.sql import functions as F

spark = DatabricksSession.builder.getOrCreate()

df = spark.createDataFrame([
    ("Alice", 34, "Engineering"),
    ("Bob", 45, "Sales"),
], ["name", "age", "department"])

df_transformed = df.withColumn("age_group",
    F.when(F.col("age") < 40, "Young").otherwise("Senior")
)

df_transformed.groupBy("age_group").count().show()
```

## Debugging Connection Issues

**NEVER modify Python code to fix connection problems.** Always fix the environment.

### General Debugging Workflow

When any connection error occurs:

1. **Check env vars**: `echo $DATABRICKS_CONFIG_PROFILE` and `echo $DATABRICKS_SERVERLESS_COMPUTE_ID`
2. **Check profiles**: `grep -E "^\[|^host" ~/.databrickscfg`
3. **Ask the user** which workspace they want to connect to
4. **Set the profile**: `export DATABRICKS_CONFIG_PROFILE=<profile>`
5. **Re-run the script unchanged**

### Error: "Cluster id or serverless are required"

Environment variables not set:
```bash
source .env
echo $DATABRICKS_SERVERLESS_COMPUTE_ID  # should be "auto"
# OR
echo $DATABRICKS_CLUSTER_ID             # should be a cluster ID
```

### Error: Authentication failures

```bash
# Check profiles
databricks auth profiles

# Re-authenticate
databricks auth login --host <workspace-url> --profile <profile>
```

### Error: "ModuleNotFoundError: No module named 'databricks.connect'"

```bash
uv sync
```

### Error: Cluster not found or stopped

```bash
databricks clusters list --profile <profile>
databricks clusters start --cluster-id <id> --profile <profile>
```

### Error: `.cache()` or `.persist()` fails

You're on serverless compute. Switch to a cluster:
```bash
unset DATABRICKS_SERVERLESS_COMPUTE_ID
export DATABRICKS_CLUSTER_ID=<cluster-id>
```

### Error: Version mismatch

The version is pinned in `pyproject.toml`. Update it there and run `uv sync`.

## Best Practices

1. **Never modify code for connection issues** — fix the environment
2. **Always use `DatabricksSession.builder.getOrCreate()`** — no parameters
3. **Default to serverless** — simpler and more cost-effective
4. **Store env vars in `.env`** — never commit credentials
5. **Write portable code** — same code should run locally and in Databricks workspace
6. **Version is pinned in `pyproject.toml`** — update there and run `uv sync`
