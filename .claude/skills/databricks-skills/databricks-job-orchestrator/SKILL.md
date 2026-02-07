---
name: databricks-job-orchestrator
description: Create, run, and monitor Databricks jobs for workflow automation. Use when scheduling notebooks, scripts, or pipelines, managing job runs, or monitoring job execution and logs.
---

# Databricks Job Orchestrator

## Overview

This skill helps you create, configure, run, and monitor Databricks jobs using the Databricks CLI. Jobs enable automated execution of notebooks, scripts, and data pipelines on schedules or triggers.

## Workflow

### 1. Create a Job from Configuration File

The recommended way to create jobs is using JSON configuration:

**Create job configuration file (job_config.json):**

```json
{
  "name": "My ETL Job",
  "tasks": [
    {
      "task_key": "extract_data",
      "notebook_task": {
        "notebook_path": "/Workspace/Users/user@example.com/extract_notebook",
        "source": "WORKSPACE"
      },
      "job_cluster_key": "default_cluster"
    }
  ],
  "job_clusters": [
    {
      "job_cluster_key": "default_cluster",
      "new_cluster": {
        "spark_version": "14.3.x-scala2.12",
        "node_type_id": "i3.xlarge",
        "num_workers": 2
      }
    }
  ]
}
```

**Create the job:**

```bash
# Create job from config file
databricks jobs create --json @job_config.json

# Or create with inline JSON
databricks jobs create --json '{
  "name": "Simple Job",
  "tasks": [{
    "task_key": "main_task",
    "notebook_task": {
      "notebook_path": "/Workspace/Users/user@example.com/notebook",
      "source": "WORKSPACE"
    },
    "existing_cluster_id": "1234-567890-abcdef12"
  }]
}'
```

### 2. Interactive Job Creation

Prompt user for job details:

```bash
#!/bin/bash

# Prompt for job details
read -p "Enter job name: " JOB_NAME
read -p "Enter notebook path (e.g., /Workspace/Users/user@example.com/notebook): " NOTEBOOK_PATH
read -p "Enter cluster ID (or press Enter to create new cluster): " CLUSTER_ID

# Build JSON config
if [[ -n "$CLUSTER_ID" ]]; then
  # Use existing cluster
  JOB_JSON=$(cat <<EOF
{
  "name": "$JOB_NAME",
  "tasks": [{
    "task_key": "main_task",
    "notebook_task": {
      "notebook_path": "$NOTEBOOK_PATH",
      "source": "WORKSPACE"
    },
    "existing_cluster_id": "$CLUSTER_ID"
  }]
}
EOF
)
else
  # Create new cluster
  read -p "Enter Spark version (e.g., 14.3.x-scala2.12): " SPARK_VERSION
  read -p "Enter node type (e.g., i3.xlarge): " NODE_TYPE
  read -p "Enter number of workers: " NUM_WORKERS

  JOB_JSON=$(cat <<EOF
{
  "name": "$JOB_NAME",
  "tasks": [{
    "task_key": "main_task",
    "notebook_task": {
      "notebook_path": "$NOTEBOOK_PATH",
      "source": "WORKSPACE"
    },
    "job_cluster_key": "job_cluster"
  }],
  "job_clusters": [{
    "job_cluster_key": "job_cluster",
    "new_cluster": {
      "spark_version": "$SPARK_VERSION",
      "node_type_id": "$NODE_TYPE",
      "num_workers": $NUM_WORKERS
    }
  }]
}
EOF
)
fi

# Create job
echo "$JOB_JSON" > /tmp/job_config.json
JOB_ID=$(databricks jobs create --json @/tmp/job_config.json | jq -r '.job_id')
echo "✅ Job created with ID: $JOB_ID"
```

### 3. Run a Job

Run an existing job and get the run ID:

```bash
# Run job by ID
databricks jobs run-now --job-id <job-id>

# Run job and capture run ID
RUN_ID=$(databricks jobs run-now --job-id <job-id> | jq -r '.run_id')
echo "Job run started with ID: $RUN_ID"
```

**Interactive job run:**

```bash
# List available jobs
databricks jobs list --output json | jq -r '.jobs[] | "\(.job_id): \(.settings.name)"'

# Prompt for job ID
read -p "Enter job ID to run: " JOB_ID

# Run job
RUN_ID=$(databricks jobs run-now --job-id "$JOB_ID" | jq -r '.run_id')
echo "✅ Job run started with ID: $RUN_ID"
```

### 4. Monitor Job Status

Check the status of a job run:

```bash
# Get run status
databricks jobs get-run --run-id <run-id>

# Get just the state
databricks jobs get-run --run-id <run-id> | jq -r '.state.life_cycle_state'

# Poll until completion
while true; do
  STATE=$(databricks jobs get-run --run-id <run-id> | jq -r '.state.life_cycle_state')
  echo "Current state: $STATE"

  if [[ "$STATE" == "TERMINATED" ]] || [[ "$STATE" == "SKIPPED" ]] || [[ "$STATE" == "INTERNAL_ERROR" ]]; then
    RESULT=$(databricks jobs get-run --run-id <run-id> | jq -r '.state.result_state')
    echo "Final result: $RESULT"
    break
  fi

  sleep 10
done
```

**Monitor with helper script:**

```bash
# Monitor job run until completion
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py monitor <run-id>
```

### 5. View Job Logs

Get output and logs from a job run:

```bash
# Get run output
databricks jobs get-run-output --run-id <run-id>

# Get run output as JSON
databricks jobs get-run-output --run-id <run-id> --output json | jq -r '.notebook_output.result'

# Get error message if failed
databricks jobs get-run --run-id <run-id> | jq -r '.state.state_message'
```

## Common Job Configurations

### Notebook Task

Run a notebook:

```json
{
  "name": "Notebook Job",
  "tasks": [{
    "task_key": "run_notebook",
    "notebook_task": {
      "notebook_path": "/Workspace/Users/user@example.com/my_notebook",
      "source": "WORKSPACE",
      "base_parameters": {
        "param1": "value1",
        "param2": "value2"
      }
    },
    "existing_cluster_id": "1234-567890-abcdef12"
  }]
}
```

### Python Script Task

Run a Python script:

```json
{
  "name": "Python Script Job",
  "tasks": [{
    "task_key": "run_script",
    "spark_python_task": {
      "python_file": "dbfs:/scripts/my_script.py",
      "parameters": ["arg1", "arg2"]
    },
    "existing_cluster_id": "1234-567890-abcdef12"
  }]
}
```

### JAR Task

Run a JAR file:

```json
{
  "name": "JAR Job",
  "tasks": [{
    "task_key": "run_jar",
    "spark_jar_task": {
      "main_class_name": "com.example.Main",
      "parameters": ["arg1", "arg2"]
    },
    "libraries": [{
      "jar": "dbfs:/jars/my-app.jar"
    }],
    "existing_cluster_id": "1234-567890-abcdef12"
  }]
}
```

### Multi-Task Workflow

Chain multiple tasks with dependencies:

```json
{
  "name": "Multi-Task Workflow",
  "tasks": [
    {
      "task_key": "extract",
      "notebook_task": {
        "notebook_path": "/Workspace/Users/user@example.com/extract",
        "source": "WORKSPACE"
      },
      "job_cluster_key": "shared_cluster"
    },
    {
      "task_key": "transform",
      "depends_on": [{"task_key": "extract"}],
      "notebook_task": {
        "notebook_path": "/Workspace/Users/user@example.com/transform",
        "source": "WORKSPACE"
      },
      "job_cluster_key": "shared_cluster"
    },
    {
      "task_key": "load",
      "depends_on": [{"task_key": "transform"}],
      "notebook_task": {
        "notebook_path": "/Workspace/Users/user@example.com/load",
        "source": "WORKSPACE"
      },
      "job_cluster_key": "shared_cluster"
    }
  ],
  "job_clusters": [{
    "job_cluster_key": "shared_cluster",
    "new_cluster": {
      "spark_version": "14.3.x-scala2.12",
      "node_type_id": "i3.xlarge",
      "num_workers": 2
    }
  }]
}
```

### Scheduled Job

Add a schedule to run automatically:

```json
{
  "name": "Daily ETL Job",
  "schedule": {
    "quartz_cron_expression": "0 0 2 * * ?",
    "timezone_id": "America/New_York",
    "pause_status": "UNPAUSED"
  },
  "tasks": [{
    "task_key": "etl_task",
    "notebook_task": {
      "notebook_path": "/Workspace/Users/user@example.com/etl_notebook",
      "source": "WORKSPACE"
    },
    "existing_cluster_id": "1234-567890-abcdef12"
  }]
}
```

**Common cron schedules:**
- Daily at 2 AM: `0 0 2 * * ?`
- Every hour: `0 0 * * * ?`
- Every 15 minutes: `0 0/15 * * * ?`
- Weekdays at 9 AM: `0 0 9 ? * MON-FRI`
- Monthly on 1st at midnight: `0 0 0 1 * ?`

## Common Operations

### List All Jobs

```bash
# List all jobs
databricks jobs list

# List jobs with details (JSON)
databricks jobs list --output json | jq -r '.jobs[] | "\(.job_id): \(.settings.name)"'

# Filter by name
databricks jobs list --output json | jq -r '.jobs[] | select(.settings.name | contains("ETL")) | "\(.job_id): \(.settings.name)"'
```

### Get Job Details

```bash
# Get job configuration
databricks jobs get --job-id <job-id>

# Get just the job name
databricks jobs get --job-id <job-id> | jq -r '.settings.name'

# Get job tasks
databricks jobs get --job-id <job-id> | jq -r '.settings.tasks[] | .task_key'
```

### Update Job Configuration

```bash
# Update job settings
databricks jobs update --job-id <job-id> --json @updated_config.json

# Reset entire job configuration
databricks jobs reset --job-id <job-id> --json @new_config.json
```

### Delete Job

```bash
# Delete job by ID
databricks jobs delete --job-id <job-id>

# Interactive delete
read -p "Enter job ID to delete: " JOB_ID
read -p "Are you sure you want to delete job $JOB_ID? (yes/no): " CONFIRM

if [[ "$CONFIRM" == "yes" ]]; then
  databricks jobs delete --job-id "$JOB_ID"
  echo "✅ Job deleted"
else
  echo "❌ Cancelled"
fi
```

### List Job Runs

```bash
# List recent runs for a job
databricks jobs list-runs --job-id <job-id>

# List all recent runs
databricks jobs list-runs --active-only false

# Get latest run for a job
databricks jobs list-runs --job-id <job-id> --limit 1 | jq -r '.runs[0]'
```

### Cancel Running Job

```bash
# Cancel a run
databricks jobs cancel-run --run-id <run-id>

# Cancel all active runs for a job
databricks jobs list-runs --job-id <job-id> --active-only true | \
  jq -r '.runs[] | .run_id' | \
  while read RUN_ID; do
    databricks jobs cancel-run --run-id "$RUN_ID"
    echo "Cancelled run $RUN_ID"
  done
```

## Troubleshooting

### Job Creation Fails

**Symptoms:** Job creation returns error

**Solutions:**
1. Validate JSON syntax:
   ```bash
   cat job_config.json | jq .
   ```

2. Check required fields:
   - `name` is required
   - At least one task is required
   - Each task needs `task_key` and a task type (notebook_task, spark_python_task, etc.)

3. Verify cluster exists:
   ```bash
   databricks clusters get --cluster-id <cluster-id>
   ```

4. Check notebook path exists:
   ```bash
   databricks workspace get-status /Workspace/path/to/notebook
   ```

### Job Fails to Start

**Symptoms:** Job run state shows INTERNAL_ERROR or fails immediately

**Solutions:**
1. Check job configuration:
   ```bash
   databricks jobs get --job-id <job-id>
   ```

2. Verify cluster can start:
   ```bash
   databricks clusters start --cluster-id <cluster-id>
   ```

3. Check for library conflicts or missing dependencies

4. Review job run error message:
   ```bash
   databricks jobs get-run --run-id <run-id> | jq -r '.state.state_message'
   ```

### Cannot View Logs

**Symptoms:** Empty output or error when getting logs

**Solutions:**
1. Ensure run has completed:
   ```bash
   databricks jobs get-run --run-id <run-id> | jq -r '.state.life_cycle_state'
   ```

2. Check if run was successful:
   ```bash
   databricks jobs get-run --run-id <run-id> | jq -r '.state.result_state'
   ```

3. For failed runs, check error message instead:
   ```bash
   databricks jobs get-run --run-id <run-id> | jq -r '.state.state_message'
   ```

### Schedule Not Working

**Symptoms:** Scheduled job not running automatically

**Solutions:**
1. Check schedule is not paused:
   ```bash
   databricks jobs get --job-id <job-id> | jq -r '.settings.schedule.pause_status'
   ```

2. Verify cron expression is valid:
   - Use https://crontab.guru for validation
   - Databricks uses Quartz cron format (6 fields)

3. Check timezone is correct:
   ```bash
   databricks jobs get --job-id <job-id> | jq -r '.settings.schedule.timezone_id'
   ```

### Cluster Auto-termination

**Symptoms:** Job cluster terminates unexpectedly

**Solutions:**
1. For job clusters, increase timeout or remove auto-termination
2. For existing clusters, ensure cluster is not set to auto-terminate
3. Use dedicated job clusters instead of shared clusters for scheduled jobs

## Best Practices

1. **Use job clusters** - Dedicated clusters for jobs are more reliable than shared clusters
2. **Parameterize notebooks** - Use base_parameters to make jobs reusable
3. **Add retry policies** - Configure retries for transient failures
4. **Monitor job runs** - Set up notifications for failures
5. **Use task dependencies** - Break complex workflows into smaller tasks
6. **Version control job configs** - Store JSON configs in git
7. **Use descriptive names** - Name jobs and tasks clearly
8. **Tag jobs** - Use tags for organization and cost tracking
9. **Test before scheduling** - Run manually before adding schedule
10. **Prompt for inputs** - Never hardcode job names, cluster IDs, or paths

## Integration with Other Skills

### With databricks-workspace-sync

Upload code first, then create job:

```bash
# Upload notebook
databricks workspace import notebook.ipynb /Workspace/Users/user@example.com/notebook --format JUPYTER

# Create job to run it
databricks jobs create --json @job_config.json
```

### With databricks-connect-config

Test locally before creating job:

```python
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.getOrCreate()

# Test your code locally first
df = spark.read.table("catalog.schema.table")
df.show()

# Once working, upload to workspace and create job
```

## Next Steps

After creating jobs:
1. Monitor job runs in the Databricks UI
2. Set up email notifications for job failures
3. Use the jobs API to programmatically manage workflows
4. Consider using Databricks Workflows for complex pipelines

## Resources

### scripts/job_helper.py

A helper script for common job operations:

```bash
# Create job from template
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py create

# List all jobs
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py list

# Run a job
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py run <job-id>

# Monitor job run until completion
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py monitor <run-id>

# Get job logs
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py logs <run-id>

# Cancel job run
python .claude/skills/databricks-job-orchestrator/scripts/job_helper.py cancel <run-id>
```

The helper provides:
- Interactive job creation with prompts
- Real-time job monitoring with progress updates
- Automatic log retrieval
- Error handling and validation
- Profile support for multiple workspaces
