#!/usr/bin/env python3
"""
Databricks Authentication Helper

Checks authentication status and helps manage profiles.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd.split(),
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_auth(profile=None):
    """Check if authenticated with Databricks."""
    cmd = ["databricks", "workspace", "list", "/", "--output", "json"]
    if profile:
        cmd.extend(["--profile", profile])

    success, stdout, stderr = run_command(cmd)
    return success


def list_profiles():
    """List available Databricks profiles."""
    config_file = Path.home() / ".databrickscfg"

    if not config_file.exists():
        print("❌ No .databrickscfg file found")
        print("   Run: databricks auth login --host <workspace-url>")
        return []

    profiles = []
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                profile_name = line[1:-1]
                profiles.append(profile_name)

    return profiles


def get_profile_info(profile="DEFAULT"):
    """Get information about a specific profile."""
    config_file = Path.home() / ".databrickscfg"

    if not config_file.exists():
        return None

    info = {}
    in_profile = False
    current_profile = None

    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()

            if line.startswith('[') and line.endswith(']'):
                current_profile = line[1:-1]
                in_profile = (current_profile == profile)
                if in_profile:
                    info = {'profile': profile}

            elif in_profile and '=' in line:
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()

    return info if info else None


def main():
    """Main function."""
    profile = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 60)
    print("Databricks Authentication Helper")
    print("=" * 60)

    # List available profiles
    print("\n📋 Available Profiles:")
    profiles = list_profiles()

    if profiles:
        for p in profiles:
            is_current = (p == profile) or (profile is None and p == "DEFAULT")
            marker = "→" if is_current else " "
            info = get_profile_info(p)

            if info and 'host' in info:
                print(f"{marker} {p}: {info['host']}")
            else:
                print(f"{marker} {p}")
    else:
        print("  No profiles configured")

    # Check authentication for target profile
    print(f"\n🔐 Authentication Status:")
    target_profile = profile if profile else "DEFAULT"

    if check_auth(profile):
        print(f"  ✅ Authenticated with profile: {target_profile}")

        # Show profile details
        info = get_profile_info(target_profile)
        if info:
            print(f"\n  Profile Details:")
            for key, value in info.items():
                if key != 'profile':
                    print(f"    {key}: {value}")

        sys.exit(0)
    else:
        print(f"  ❌ Not authenticated with profile: {target_profile}")

        # Provide helpful guidance
        info = get_profile_info(target_profile)
        if info and 'host' in info:
            print(f"\n  Run: databricks auth login --host {info['host']} --profile {target_profile}")
        else:
            print(f"\n  Run: databricks auth login --host <workspace-url> --profile {target_profile}")

        sys.exit(1)


if __name__ == "__main__":
    main()
