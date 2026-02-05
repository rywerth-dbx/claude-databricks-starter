#!/usr/bin/env python3
"""
Databricks Connect Connection Tester

Tests Databricks Connect configuration and verifies connectivity.
"""

import sys
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


def check_profile(profile):
    """Check if profile exists in .databrickscfg."""
    config_file = Path.home() / ".databrickscfg"

    if not config_file.exists():
        return False, "No .databrickscfg file found"

    with open(config_file, 'r') as f:
        content = f.read()
        if f"[{profile}]" in content:
            return True, f"Profile '{profile}' found"
        else:
            return False, f"Profile '{profile}' not found in .databrickscfg"


def create_session(profile=None, cluster_id=None):
    """Create a Databricks session."""
    from databricks.connect import DatabricksSession

    builder = DatabricksSession.builder

    if profile:
        builder = builder.profile(profile)

    if cluster_id:
        builder = builder.clusterId(cluster_id)

    spark = builder.getOrCreate()
    return spark


def test_connection(profile=None, cluster_id=None):
    """Test connection to Databricks."""
    print("=" * 60)
    print("Databricks Connect Connection Test")
    print("=" * 60)

    # Check databricks-connect installation
    print("\n1. Checking databricks-connect installation...")
    installed, version = check_databricks_connect()

    if not installed:
        print(f"  ❌ databricks-connect not installed: {version}")
        print(f"\n  Install with: pip install databricks-connect")
        return False
    else:
        print(f"  ✅ databricks-connect installed: {version}")

    # Check profile if specified
    if profile:
        print(f"\n2. Checking profile '{profile}'...")
        exists, message = check_profile(profile)
        if not exists:
            print(f"  ❌ {message}")
            print(f"\n  Authenticate with: databricks auth login --host <workspace-url> --profile {profile}")
            return False
        else:
            print(f"  ✅ {message}")
    else:
        print(f"\n2. Using DEFAULT profile...")
        exists, message = check_profile("DEFAULT")
        if not exists:
            print(f"  ⚠️  {message}")
            print(f"     Attempting connection anyway (may use environment variables)...")

    # Create session
    print("\n3. Creating Databricks session...")
    config_desc = []
    if profile:
        config_desc.append(f"profile='{profile}'")
    if cluster_id:
        config_desc.append(f"cluster_id='{cluster_id}'")
    else:
        config_desc.append("serverless")

    print(f"  Configuration: {', '.join(config_desc)}")

    spark = create_session(profile=profile, cluster_id=cluster_id)
    print(f"  ✅ Session created successfully")

    # Get session info
    print("\n4. Retrieving session information...")
    print(f"  Spark version: {spark.version}")

    # Get cluster info
    cluster_info = spark.conf.get('spark.databricks.clusterUsageTags.clusterId', None)
    if cluster_info:
        print(f"  Cluster ID: {cluster_info}")
    else:
        print(f"  Compute: Serverless")

    # Test query
    print("\n5. Running test query...")
    count = spark.range(100).count()
    print(f"  ✅ Test query successful: spark.range(100).count() = {count}")

    # List a catalog (if Unity Catalog is available)
    print("\n6. Testing Unity Catalog access...")
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
    parser = argparse.ArgumentParser(description="Test Databricks Connect configuration")
    parser.add_argument("--profile", help="Databricks profile to use")
    parser.add_argument("--cluster-id", help="Cluster ID to connect to")

    args = parser.parse_args()

    try:
        success = test_connection(profile=args.profile, cluster_id=args.cluster_id)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"1. Verify authentication:")
        print(f"   databricks auth describe")
        print(f"   databricks workspace list /")
        print(f"2. Re-authenticate if needed:")
        print(f"   databricks auth login --host <workspace-url>")
        print(f"3. Check databricks-connect installation:")
        print(f"   pip show databricks-connect")
        if args.cluster_id:
            print(f"4. Verify cluster is running:")
            print(f"   databricks clusters get --cluster-id {args.cluster_id}")
        sys.exit(1)


if __name__ == "__main__":
    main()
