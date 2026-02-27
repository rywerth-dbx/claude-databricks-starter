#!/usr/bin/env python3
"""
Databricks Connect Connection Tester

Tests Databricks Connect configuration and verifies connectivity.
Validates that required environment variables are set before attempting connection.
"""

import sys
import os
import argparse
from pathlib import Path


def check_databricks_connect():
    """Check if databricks-connect is installed."""
    try:
        import databricks.connect
        from databricks.connect import DatabricksSession
        return True, databricks.connect.__version__
    except ImportError as e:
        return False, str(e)


def check_environment_variables():
    """Check if required environment variables are set."""
    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")
    serverless = os.environ.get("DATABRICKS_SERVERLESS_COMPUTE_ID")
    cluster_id = os.environ.get("DATABRICKS_CLUSTER_ID")

    issues = []
    warnings = []

    # Profile is optional - will default to DEFAULT if not set
    if not profile:
        profile = "DEFAULT"
        warnings.append("DATABRICKS_CONFIG_PROFILE not set, will use DEFAULT profile")

    # Compute must be specified
    if not serverless and not cluster_id:
        issues.append("Either DATABRICKS_SERVERLESS_COMPUTE_ID or DATABRICKS_CLUSTER_ID must be set")

    return len(issues) == 0, issues, warnings, profile, serverless, cluster_id


def check_profile(profile):
    """Check if profile exists in .databrickscfg and get workspace URL."""
    config_file = Path.home() / ".databrickscfg"

    if not config_file.exists():
        return False, "No .databrickscfg file found", None

    with open(config_file, 'r') as f:
        content = f.read()
        if f"[{profile}]" not in content:
            return False, f"Profile '{profile}' not found in .databrickscfg", None

        # Extract workspace URL for this profile
        lines = content.split('\n')
        in_profile = False
        workspace_url = None

        for line in lines:
            if f"[{profile}]" in line:
                in_profile = True
                continue
            if in_profile:
                if line.startswith('['):  # Next profile section
                    break
                if line.strip().startswith('host'):
                    workspace_url = line.split('=', 1)[1].strip()
                    break

        return True, f"Profile '{profile}' found", workspace_url


def create_session():
    """Create a Databricks session using environment variables only."""
    from databricks.connect import DatabricksSession

    # This is the ONLY correct way - no hardcoded configuration
    spark = DatabricksSession.builder.getOrCreate()
    return spark


def test_connection():
    """Test connection to Databricks using environment variables."""
    print("=" * 60)
    print("Databricks Connect Connection Test")
    print("=" * 60)

    # Check databricks-connect installation
    print("\n1. Checking databricks-connect installation...")
    installed, version = check_databricks_connect()

    if not installed:
        print(f"  ❌ databricks-connect not installed: {version}")
        print(f"\n  Install with: uv sync")
        return False
    else:
        print(f"  ✅ databricks-connect installed: {version}")

    # Check environment variables
    print("\n2. Checking environment variables...")
    env_valid, issues, warnings, profile, serverless, cluster_id = check_environment_variables()

    if not env_valid:
        print("  ❌ Required environment variables not set:")
        for issue in issues:
            print(f"     - {issue}")
        print("\n  Set environment variables:")
        print("     export DATABRICKS_SERVERLESS_COMPUTE_ID=auto")
        print("  OR")
        print("     export DATABRICKS_CLUSTER_ID=<cluster-id>")
        print("\n  Optionally set profile (defaults to DEFAULT):")
        print("     export DATABRICKS_CONFIG_PROFILE=<your-profile>")
        print("\n  You can also load from .env file:")
        print("     source .env")
        return False

    # Show warnings
    if warnings:
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    print(f"  ✅ Environment variables configured:")
    print(f"     DATABRICKS_CONFIG_PROFILE={profile}")
    if serverless:
        print(f"     DATABRICKS_SERVERLESS_COMPUTE_ID={serverless}")
    if cluster_id:
        print(f"     DATABRICKS_CLUSTER_ID={cluster_id}")

    # Check profile exists in config
    print(f"\n3. Checking profile '{profile}'...")
    exists, message, workspace_url = check_profile(profile)
    if not exists:
        print(f"  ❌ {message}")
        print(f"\n  Available profiles:")
        try:
            import subprocess
            result = subprocess.run(['databricks', 'auth', 'profiles'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"     {result.stdout}")
        except Exception:
            pass
        print(f"\n  Authenticate with: databricks auth login --host <workspace-url> --profile {profile}")
        print(f"\n  Or set DATABRICKS_CONFIG_PROFILE to an existing profile:")
        print(f"     export DATABRICKS_CONFIG_PROFILE=<profile-name>")
        return False
    else:
        print(f"  ✅ {message}")
        if workspace_url:
            print(f"  📍 Workspace: {workspace_url}")
            if profile == "DEFAULT":
                print(f"\n  💡 Using DEFAULT profile. To use a different workspace:")
                print(f"     export DATABRICKS_CONFIG_PROFILE=<profile-name>")
                print(f"     See available profiles: databricks auth profiles")

    # Create session
    print("\n4. Creating Databricks session...")
    config_desc = []
    config_desc.append(f"profile='{profile}'")
    if serverless:
        config_desc.append("serverless")
    if cluster_id:
        config_desc.append(f"cluster_id='{cluster_id}'")

    print(f"  Configuration: {', '.join(config_desc)}")

    spark = create_session()
    print(f"  ✅ Session created successfully")

    # Get session info
    print("\n5. Retrieving session information...")
    print(f"  Spark version: {spark.version}")

    # Get cluster info
    cluster_info = spark.conf.get('spark.databricks.clusterUsageTags.clusterId', None)
    if cluster_info:
        print(f"  Cluster ID: {cluster_info}")
    else:
        print(f"  Compute: Serverless")

    # Test query
    print("\n6. Running test query...")
    count = spark.range(100).count()
    print(f"  ✅ Test query successful: spark.range(100).count() = {count}")

    # List a catalog (if Unity Catalog is available)
    print("\n7. Testing Unity Catalog access...")
    catalogs = spark.sql("SHOW CATALOGS").collect()
    if catalogs:
        print(f"  ✅ Unity Catalog accessible")
        print(f"  Available catalogs:")
        for cat in catalogs[:5]:  # Show first 5
            print(f"    - {cat[0]}")
        if len(catalogs) > 5:
            print(f"    ... and {len(catalogs) - 5} more")
    else:
        print(f"  ℹ️  No catalogs found (Unity Catalog may not be enabled)")

    print("\n" + "=" * 60)
    print("✅ All tests passed! Connection is working.")
    print("=" * 60)

    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test Databricks Connect configuration using environment variables",
        epilog="Environment variables required: DATABRICKS_CONFIG_PROFILE and either DATABRICKS_SERVERLESS_COMPUTE_ID or DATABRICKS_CLUSTER_ID"
    )

    args = parser.parse_args()

    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"1. Ensure environment variables are set:")
        print(f"   source .env")
        print(f"2. Verify authentication:")
        print(f"   databricks auth profiles")
        print(f"   databricks workspace list /")
        print(f"3. Re-authenticate if needed:")
        print(f"   databricks auth login --host <workspace-url> --profile <profile-name>")
        print(f"4. Check databricks-connect installation:")
        print(f"   uv run python -c \"import databricks.connect; print(databricks.connect.__version__)\"")
        print(f"   If not installed, run: uv sync")
        cluster_id = os.environ.get("DATABRICKS_CLUSTER_ID")
        if cluster_id:
            print(f"5. Verify cluster is running:")
            print(f"   databricks clusters get --cluster-id {cluster_id}")
        sys.exit(1)


if __name__ == "__main__":
    main()
