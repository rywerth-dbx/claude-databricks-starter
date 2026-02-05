#!/usr/bin/env python3
"""
Databricks Workspace Sync Helper

Helps upload and download files between local filesystem and Databricks workspace.
"""

import sys
import subprocess
import argparse
import json
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


def detect_format(file_path):
    """Detect appropriate format for file."""
    ext = Path(file_path).suffix.lower()

    if ext == '.py':
        return '--language', 'PYTHON'
    elif ext == '.sql':
        return '--language', 'SQL'
    elif ext == '.ipynb':
        return '--format', 'JUPYTER'
    elif ext in ['.r', '.R']:
        return '--language', 'R'
    elif ext == '.scala':
        return '--language', 'SCALA'
    else:
        return '--format', 'AUTO'


def upload_file(local_path, workspace_path, profile=None, overwrite=False):
    """Upload a file to workspace."""
    print(f"Uploading {local_path} to {workspace_path}...")

    # Detect format
    flag, value = detect_format(local_path)

    # Build command
    cmd = ['databricks', 'workspace', 'import', local_path, workspace_path, flag, value]

    if overwrite:
        cmd.append('--overwrite')

    if profile:
        cmd.extend(['--profile', profile])

    # Execute
    success, stdout, stderr = run_command(cmd)

    if success:
        print(f"  ✅ Upload successful")
        return True
    else:
        print(f"  ❌ Upload failed: {stderr}")
        return False


def upload_directory(local_dir, workspace_path, profile=None, overwrite=False):
    """Upload a directory to workspace."""
    print(f"Uploading directory {local_dir} to {workspace_path}...")

    # Build command
    cmd = ['databricks', 'workspace', 'import-dir', local_dir, workspace_path]

    if overwrite:
        cmd.append('--overwrite')

    if profile:
        cmd.extend(['--profile', profile])

    # Execute
    success, stdout, stderr = run_command(cmd)

    if success:
        print(f"  ✅ Directory upload successful")
        return True
    else:
        print(f"  ❌ Directory upload failed: {stderr}")
        return False


def download_file(workspace_path, local_path, profile=None, format='SOURCE'):
    """Download a file from workspace."""
    print(f"Downloading {workspace_path} to {local_path}...")

    # Build command
    cmd = ['databricks', 'workspace', 'export', workspace_path, local_path, '--format', format]

    if profile:
        cmd.extend(['--profile', profile])

    # Execute
    success, stdout, stderr = run_command(cmd)

    if success:
        print(f"  ✅ Download successful")
        return True
    else:
        print(f"  ❌ Download failed: {stderr}")
        return False


def download_directory(workspace_path, local_dir, profile=None):
    """Download a directory from workspace."""
    print(f"Downloading directory {workspace_path} to {local_dir}...")

    # Build command
    cmd = ['databricks', 'workspace', 'export-dir', workspace_path, local_dir]

    if profile:
        cmd.extend(['--profile', profile])

    # Execute
    success, stdout, stderr = run_command(cmd)

    if success:
        print(f"  ✅ Directory download successful")
        return True
    else:
        print(f"  ❌ Directory download failed: {stderr}")
        return False


def list_workspace(workspace_path, profile=None):
    """List contents of workspace directory."""
    print(f"Listing {workspace_path}...")

    # Build command
    cmd = ['databricks', 'workspace', 'list', workspace_path, '--output', 'json']

    if profile:
        cmd.extend(['--profile', profile])

    # Execute
    success, stdout, stderr = run_command(cmd)

    if success:
        try:
            data = json.loads(stdout)
            objects = data.get('objects', [])

            if not objects:
                print(f"  (empty directory)")
                return True

            print(f"\n  Found {len(objects)} items:")
            for obj in objects:
                obj_type = obj.get('object_type', 'UNKNOWN')
                path = obj.get('path', '')
                name = Path(path).name

                if obj_type == 'DIRECTORY':
                    print(f"    📁 {name}/")
                elif obj_type == 'NOTEBOOK':
                    print(f"    📓 {name}")
                elif obj_type == 'FILE':
                    print(f"    📄 {name}")
                else:
                    print(f"    ❓ {name} ({obj_type})")

            return True
        except json.JSONDecodeError:
            print(f"  ⚠️  Could not parse response")
            print(f"  Raw output: {stdout}")
            return False
    else:
        print(f"  ❌ List failed: {stderr}")
        return False


def get_workspace_status(workspace_path, profile=None):
    """Get status of workspace path."""
    cmd = ['databricks', 'workspace', 'get-status', workspace_path, '--output', 'json']

    if profile:
        cmd.extend(['--profile', profile])

    success, stdout, stderr = run_command(cmd)

    if success:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None
    else:
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Databricks Workspace Sync Helper")
    parser.add_argument('operation', choices=['upload', 'upload-dir', 'download', 'download-dir', 'list'],
                        help="Operation to perform")
    parser.add_argument('source', nargs='?', help="Source path (local for upload, workspace for download)")
    parser.add_argument('destination', nargs='?', help="Destination path")
    parser.add_argument('--profile', help="Databricks profile to use")
    parser.add_argument('--overwrite', action='store_true', help="Overwrite existing files")
    parser.add_argument('--format', default='SOURCE', help="Export format for download (SOURCE, JUPYTER, HTML, DBC)")

    args = parser.parse_args()

    # Interactive mode if arguments missing
    if not args.source:
        if args.operation == 'list':
            args.source = input("Enter workspace path to list: ").strip()
        elif args.operation in ['upload', 'upload-dir']:
            args.source = input("Enter local path: ").strip()
        else:
            args.source = input("Enter workspace path: ").strip()

    if not args.destination and args.operation != 'list':
        if args.operation in ['upload', 'upload-dir']:
            args.destination = input("Enter workspace destination path: ").strip()
        else:
            args.destination = input("Enter local destination path: ").strip()

    # Perform operation
    success = False

    if args.operation == 'upload':
        success = upload_file(args.source, args.destination, args.profile, args.overwrite)

    elif args.operation == 'upload-dir':
        success = upload_directory(args.source, args.destination, args.profile, args.overwrite)

    elif args.operation == 'download':
        success = download_file(args.source, args.destination, args.profile, args.format)

    elif args.operation == 'download-dir':
        success = download_directory(args.source, args.destination, args.profile)

    elif args.operation == 'list':
        success = list_workspace(args.source, args.profile)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
