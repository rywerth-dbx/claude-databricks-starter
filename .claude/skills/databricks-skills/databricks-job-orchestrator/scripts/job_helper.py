#!/usr/bin/env python3
"""
Databricks Job Helper

Manages Databricks jobs - create, run, monitor, and manage job execution.
"""

import sys
import subprocess
import argparse
import json
import time
from pathlib import Path


def run_command(cmd):
    """Run a shell command and return result."""
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd.split(),
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def list_jobs(profile=None):
    """List all jobs."""
    print("Listing all jobs...")

    cmd = ['databricks', 'jobs', 'list', '--output', 'json']
    if profile:
        cmd.extend(['--profile', profile])

    success, stdout, stderr = run_command(cmd)

    if success:
        try:
            data = json.loads(stdout)
            jobs = data.get('jobs', [])

            if not jobs:
                print("  No jobs found")
                return True

            print(f"\n  Found {len(jobs)} jobs:\n")
            for job in jobs:
                job_id = job.get('job_id')
                job_name = job.get('settings', {}).get('name', 'Unnamed')
                print(f"    {job_id}: {job_name}")

            return True
        except json.JSONDecodeError:
            print(f"  Error parsing response")
            return False
    else:
        print(f"  ❌ Failed to list jobs: {stderr}")
        return False


def create_job(profile=None):
    """Create a job interactively."""
    print("Creating a new job...")

    # Prompt for job details
    job_name = input("  Enter job name: ").strip()
    notebook_path = input("  Enter notebook path (e.g., /Workspace/Users/user@example.com/notebook): ").strip()

    cluster_choice = input("  Use existing cluster? (y/n): ").strip().lower()

    if cluster_choice == 'y':
        cluster_id = input("  Enter cluster ID: ").strip()

        job_config = {
            "name": job_name,
            "tasks": [{
                "task_key": "main_task",
                "notebook_task": {
                    "notebook_path": notebook_path,
                    "source": "WORKSPACE"
                },
                "existing_cluster_id": cluster_id
            }]
        }
    else:
        spark_version = input("  Enter Spark version (e.g., 14.3.x-scala2.12): ").strip()
        node_type = input("  Enter node type (e.g., i3.xlarge): ").strip()
        num_workers = input("  Enter number of workers: ").strip()

        job_config = {
            "name": job_name,
            "tasks": [{
                "task_key": "main_task",
                "notebook_task": {
                    "notebook_path": notebook_path,
                    "source": "WORKSPACE"
                },
                "job_cluster_key": "job_cluster"
            }],
            "job_clusters": [{
                "job_cluster_key": "job_cluster",
                "new_cluster": {
                    "spark_version": spark_version,
                    "node_type_id": node_type,
                    "num_workers": int(num_workers)
                }
            }]
        }

    # Save config to temp file
    config_file = Path("/tmp/job_config.json")
    with open(config_file, 'w') as f:
        json.dump(job_config, f, indent=2)

    print(f"\n  Job configuration saved to {config_file}")

    # Create job
    cmd = ['databricks', 'jobs', 'create', '--json', f'@{config_file}']
    if profile:
        cmd.extend(['--profile', profile])

    success, stdout, stderr = run_command(cmd)

    if success:
        try:
            result = json.loads(stdout)
            job_id = result.get('job_id')
            print(f"\n  ✅ Job created successfully with ID: {job_id}")
            return True
        except json.JSONDecodeError:
            print(f"\n  ✅ Job created (could not parse job ID)")
            return True
    else:
        print(f"\n  ❌ Failed to create job: {stderr}")
        return False


def run_job(job_id, profile=None):
    """Run a job and return run ID."""
    print(f"Running job {job_id}...")

    cmd = ['databricks', 'jobs', 'run-now', '--job-id', str(job_id)]
    if profile:
        cmd.extend(['--profile', profile])

    success, stdout, stderr = run_command(cmd)

    if success:
        try:
            result = json.loads(stdout)
            run_id = result.get('run_id')
            print(f"  ✅ Job run started with ID: {run_id}")
            return run_id
        except json.JSONDecodeError:
            print(f"  ⚠️  Job started but could not parse run ID")
            return None
    else:
        print(f"  ❌ Failed to run job: {stderr}")
        return None


def monitor_run(run_id, profile=None):
    """Monitor a job run until completion."""
    print(f"Monitoring job run {run_id}...")

    terminal_states = ['TERMINATED', 'SKIPPED', 'INTERNAL_ERROR']
    success_states = ['SUCCESS']

    while True:
        cmd = ['databricks', 'jobs', 'get-run', '--run-id', str(run_id), '--output', 'json']
        if profile:
            cmd.extend(['--profile', profile])

        success, stdout, stderr = run_command(cmd)

        if not success:
            print(f"  ❌ Failed to get run status: {stderr}")
            return False

        try:
            data = json.loads(stdout)
            state = data.get('state', {})
            life_cycle_state = state.get('life_cycle_state')
            result_state = state.get('result_state')

            print(f"  Current state: {life_cycle_state}", end='')
            if result_state:
                print(f" ({result_state})")
            else:
                print()

            if life_cycle_state in terminal_states:
                print(f"\n  Run completed with result: {result_state}")

                if result_state in success_states:
                    print(f"  ✅ Job run succeeded")
                    return True
                else:
                    print(f"  ❌ Job run failed")
                    state_message = state.get('state_message', 'No error message')
                    print(f"  Error: {state_message}")
                    return False

            time.sleep(10)

        except json.JSONDecodeError:
            print(f"  ⚠️  Could not parse run status")
            time.sleep(10)


def get_logs(run_id, profile=None):
    """Get logs from a job run."""
    print(f"Retrieving logs for run {run_id}...")

    cmd = ['databricks', 'jobs', 'get-run-output', '--run-id', str(run_id), '--output', 'json']
    if profile:
        cmd.extend(['--profile', profile])

    success, stdout, stderr = run_command(cmd)

    if success:
        try:
            data = json.loads(stdout)

            # Try to get notebook output
            notebook_output = data.get('notebook_output', {})
            result = notebook_output.get('result')

            if result:
                print(f"\n  Notebook output:")
                print(f"  {result}")
                return True

            # Try to get error
            error = data.get('error')
            if error:
                print(f"\n  Error output:")
                print(f"  {error}")
                return True

            print(f"\n  No output available")
            return True

        except json.JSONDecodeError:
            print(f"  Raw output:")
            print(f"  {stdout}")
            return True
    else:
        print(f"  ❌ Failed to get logs: {stderr}")
        return False


def cancel_run(run_id, profile=None):
    """Cancel a job run."""
    print(f"Cancelling job run {run_id}...")

    cmd = ['databricks', 'jobs', 'cancel-run', '--run-id', str(run_id)]
    if profile:
        cmd.extend(['--profile', profile])

    success, stdout, stderr = run_command(cmd)

    if success:
        print(f"  ✅ Job run cancelled")
        return True
    else:
        print(f"  ❌ Failed to cancel run: {stderr}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Databricks Job Helper")
    parser.add_argument('operation', choices=['create', 'list', 'run', 'monitor', 'logs', 'cancel'],
                        help="Operation to perform")
    parser.add_argument('id', nargs='?', help="Job ID or Run ID (depending on operation)")
    parser.add_argument('--profile', help="Databricks profile to use")

    args = parser.parse_args()

    # Perform operation
    success = False

    if args.operation == 'create':
        success = create_job(profile=args.profile)

    elif args.operation == 'list':
        success = list_jobs(profile=args.profile)

    elif args.operation == 'run':
        if not args.id:
            job_id = input("Enter job ID to run: ").strip()
        else:
            job_id = args.id

        run_id = run_job(job_id, profile=args.profile)
        success = run_id is not None

        # Ask if user wants to monitor
        if success:
            monitor = input("\nMonitor this run? (y/n): ").strip().lower()
            if monitor == 'y':
                monitor_run(run_id, profile=args.profile)

    elif args.operation == 'monitor':
        if not args.id:
            run_id = input("Enter run ID to monitor: ").strip()
        else:
            run_id = args.id

        success = monitor_run(run_id, profile=args.profile)

    elif args.operation == 'logs':
        if not args.id:
            run_id = input("Enter run ID to get logs: ").strip()
        else:
            run_id = args.id

        success = get_logs(run_id, profile=args.profile)

    elif args.operation == 'cancel':
        if not args.id:
            run_id = input("Enter run ID to cancel: ").strip()
        else:
            run_id = args.id

        confirm = input(f"Are you sure you want to cancel run {run_id}? (yes/no): ").strip()
        if confirm == 'yes':
            success = cancel_run(run_id, profile=args.profile)
        else:
            print("Cancelled")
            success = True

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
