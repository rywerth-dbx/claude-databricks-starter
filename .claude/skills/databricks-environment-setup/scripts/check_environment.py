#!/usr/bin/env python3
"""
Databricks Environment Checker

Diagnoses your Databricks development environment and provides recommendations.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_cli():
    """Check Databricks CLI installation."""
    print("🔍 Checking Databricks CLI...")
    success, stdout, stderr = run_command("databricks --version")

    if success and stdout:
        version = stdout.split()[-1] if stdout.split() else "unknown"
        print(f"  ✅ Databricks CLI installed: {version}")

        # Check version is >= 0.205
        try:
            major, minor, patch = version.split('.')[:3]
            if int(minor) >= 205 or int(major) > 0:
                print(f"  ✅ Version is up to date (>= 0.205.0)")
                return True
            else:
                print(f"  ⚠️  Version {version} is outdated. Recommend upgrading to 0.205+")
                print(f"     Run: brew upgrade databricks (macOS) or reinstall")
                return False
        except:
            print(f"  ⚠️  Could not parse version: {version}")
            return False
    else:
        print(f"  ❌ Databricks CLI not found")
        print(f"     Install: brew install databricks (macOS)")
        print(f"            : curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh (Linux)")
        print(f"            : winget install Databricks.DatabricksCLI (Windows)")
        return False


def check_databricks_connect():
    """Check databricks-connect installation."""
    print("\n🔍 Checking databricks-connect...")
    success, stdout, stderr = run_command(
        "uv run python -c \"import databricks.connect; print(databricks.connect.__version__)\""
    )

    if success and stdout:
        version = stdout.strip()
        print(f"  ✅ databricks-connect installed: {version}")

        try:
            major = int(version.split('.')[0])
            if major >= 17:
                print(f"  ✅ Version is current")
            else:
                print(f"  ⚠️  Version {version} may be outdated. Update pyproject.toml and run: uv sync")
        except:
            pass
        return True
    else:
        print(f"  ❌ databricks-connect not found")
        print(f"     Install by running: uv sync")
        return False


def check_python():
    """Check Python version."""
    print("\n🔍 Checking Python...")
    version = sys.version.split()[0]
    major, minor = sys.version_info[:2]

    print(f"  ℹ️  Python version: {version}")

    if major == 3 and minor >= 10:
        if minor == 12:
            print(f"  ✅ Python 3.12 - Recommended for databricks-connect 18.x")
        else:
            print(f"  ✅ Python 3.{minor} - Compatible")
        return True
    else:
        print(f"  ⚠️  Python {version} may not be compatible")
        print(f"     Recommend: Python 3.12 for databricks-connect 18.x")
        return False


def check_venv():
    """Check if uv virtual environment exists."""
    print("\n🔍 Checking virtual environment...")
    venv_path = Path(".venv")

    if venv_path.exists() and (venv_path / "bin" / "python").exists():
        print(f"  ✅ uv virtual environment found at .venv/")
        return True
    else:
        print(f"  ❌ No .venv directory found")
        print(f"     Run: uv sync")
        return False


def check_pyspark_conflict():
    """Check for pyspark installation (conflicts with databricks-connect)."""
    print("\n🔍 Checking for pyspark conflicts...")
    success, stdout, stderr = run_command("pip show pyspark")

    if success and stdout:
        print(f"  ⚠️  pyspark is installed - this conflicts with databricks-connect!")
        print(f"     Run: pip uninstall pyspark")
        return False
    else:
        print(f"  ✅ No pyspark conflict detected")
        return True


def check_auth():
    """Check if Databricks authentication is configured."""
    print("\n🔍 Checking authentication...")

    # Check for .databrickscfg
    home = Path.home()
    config_file = home / ".databrickscfg"

    if config_file.exists():
        print(f"  ✅ .databrickscfg file found")

        # Try to list workspaces (quick auth test)
        success, stdout, stderr = run_command("databricks workspace list / --output json 2>&1")
        if "Error: " not in stdout and "Error: " not in stderr:
            print(f"  ✅ CLI authentication working")
            return True
        else:
            print(f"  ⚠️  Authentication may need refresh")
            print(f"     Run: databricks auth login --host <your-workspace-url>")
            return False
    else:
        print(f"  ℹ️  No .databrickscfg found - authentication not configured")
        print(f"     Use databricks-auth-manager skill to set up authentication")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("Databricks Environment Diagnostic Tool")
    print("=" * 60)

    checks = {
        "Databricks CLI": check_cli(),
        "databricks-connect": check_databricks_connect(),
        "Python Version": check_python(),
        "Virtual Environment": check_venv(),
        "No PySpark Conflict": check_pyspark_conflict(),
        "Authentication": check_auth(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(checks.values())
    total = len(checks)

    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")

    print(f"\n{passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 Your environment is ready for Databricks development!")
    else:
        print("\n⚠️  Some issues detected. Review recommendations above.")
        print("\nNext steps:")
        print("1. Fix any critical issues (CLI, databricks-connect)")
        print("2. Use databricks-auth-manager skill to configure authentication")
        print("3. Use databricks-connect-config skill to set up remote execution")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
