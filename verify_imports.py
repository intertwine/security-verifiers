#!/usr/bin/env python
"""Verify that all security-verifiers environment imports are working correctly."""

import importlib
import sys
import traceback
from pathlib import Path

# ANSI color codes for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{text:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_success(text):
    """Print success message in green."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    """Print error message in red."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text):
    """Print warning message in yellow."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text):
    """Print info message."""
    print(f"  {text}")


# Define all environments and their expected exports
ENVIRONMENTS = {
    "sv_env_network_logs": {
        "classes": ["NetworkLogsEnvironment", "NetworkLogsVerifier"],
        "description": "Network logs anomaly detection",
    },
    "sv_env_phishing_detection": {
        "classes": ["PhishingDetectionEnvironment", "PhishingDetectionVerifier"],
        "description": "Phishing email detection",
    },
    "sv_env_redteam_defense": {
        "classes": ["RedTeamDefenseEnvironment", "RedTeamDefenseVerifier"],
        "description": "Defensive AI assistant security",
    },
    "sv_env_redteam_attack": {
        "classes": ["RedTeamAttackEnvironment", "RedTeamAttackVerifier"],
        "description": "Red team attack generation",
    },
    "sv_env_code_vulnerability": {
        "classes": ["CodeVulnerabilityEnvironment", "CodeVulnerabilityVerifier"],
        "description": "Code vulnerability assessment",
    },
    "sv_env_config_verification": {
        "classes": ["ConfigVerificationEnvironment", "ConfigVerificationVerifier"],
        "description": "Configuration security verification",
    },
}


def verify_python_path():
    """Check Python path configuration."""
    print_header("Python Path Configuration")

    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")

    print("\nRelevant paths in sys.path:")
    found_env_paths = False
    for path in sys.path:
        if "security-verifiers" in path:
            print_info(path)
            found_env_paths = True

    if not found_env_paths:
        print_warning("No security-verifiers paths found in sys.path")

    return found_env_paths


def verify_environment(env_name, env_info):
    """Verify a single environment package."""
    print(f"\n{BOLD}Testing {env_name}{RESET}")
    print(f"  Description: {env_info['description']}")

    success = True

    # Test package import
    try:
        module = importlib.import_module(env_name)
        print_success("Package import successful")

        # Check for expected classes
        for class_name in env_info["classes"]:
            if hasattr(module, class_name):
                print_success(f"Found {class_name}")
            else:
                print_error(f"Missing {class_name}")
                success = False

        # Check for __all__ attribute
        if hasattr(module, "__all__"):
            print_info(f"__all__ = {module.__all__}")
        else:
            print_warning("No __all__ attribute defined")

        # Check for version
        if hasattr(module, "__version__"):
            print_info(f"Version: {module.__version__}")

        # Test environment.py and verifier.py imports
        try:
            env_module = importlib.import_module(f"{env_name}.environment")
            print_success("environment.py import successful")
        except ImportError as e:
            print_error(f"environment.py import failed: {e}")
            success = False

        try:
            ver_module = importlib.import_module(f"{env_name}.verifier")
            print_success("verifier.py import successful")
        except ImportError as e:
            print_error(f"verifier.py import failed: {e}")
            success = False

    except ImportError as e:
        print_error(f"Package import failed: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        success = False

    return success


def verify_cross_imports():
    """Test importing multiple environments together."""
    print_header("Cross-Import Test")

    try:
        # Try importing all environments at once
        imports = []
        for env_name in ENVIRONMENTS:
            module = importlib.import_module(env_name)
            imports.append((env_name, module))

        print_success(f"Successfully imported all {len(imports)} environments")

        # Test that we can instantiate classes
        instantiated = 0
        for env_name, env_info in ENVIRONMENTS.items():
            try:
                module = importlib.import_module(env_name)
                for class_name in env_info["classes"]:
                    if hasattr(module, class_name):
                        cls = getattr(module, class_name)
                        # Try to instantiate (may fail if requires args)
                        try:
                            instance = cls()
                            instantiated += 1
                        except Exception:
                            # Some classes may require arguments
                            pass
            except Exception:
                pass

        if instantiated > 0:
            print_success(f"Successfully instantiated {instantiated} classes")

        return True

    except Exception as e:
        print_error(f"Cross-import test failed: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False


def check_file_structure():
    """Verify the file structure of environments."""
    print_header("File Structure Check")

    env_dir = Path.cwd() / "environments"
    if not env_dir.exists():
        print_error("environments/ directory not found")
        return False

    all_good = True
    for env_name in ENVIRONMENTS:
        env_path = env_dir / env_name.replace("_", "-")
        if env_path.exists():
            print_success(f"{env_name.replace('_', '-')} directory exists")

            # Check for required files
            src_path = env_path / "src" / env_name
            required_files = ["__init__.py", "environment.py", "verifier.py", "interfaces.py"]

            for file_name in required_files:
                file_path = src_path / file_name
                if file_path.exists():
                    print_info(f"  ✓ {file_name}")
                else:
                    print_info(f"  ✗ {file_name} missing")
                    if file_name in ["environment.py", "verifier.py"]:
                        all_good = False
        else:
            print_error(f"{env_name.replace('_', '-')} directory not found")
            all_good = False

    return all_good


def main():
    """Main verification routine."""
    print_header("Security Verifiers Import Verification")

    # Track overall success
    all_tests_passed = True

    # Check Python path
    if not verify_python_path():
        print_warning("\nPython path may not be configured correctly")
        all_tests_passed = False

    # Check file structure
    if not check_file_structure():
        print_warning("\nSome required files are missing")
        all_tests_passed = False

    # Test each environment
    print_header("Individual Environment Tests")

    results = {}
    for env_name, env_info in ENVIRONMENTS.items():
        success = verify_environment(env_name, env_info)
        results[env_name] = success
        if not success:
            all_tests_passed = False

    # Test cross-imports
    if not verify_cross_imports():
        all_tests_passed = False

    # Summary
    print_header("Summary")

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    print(f"Environments tested: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")

    if all_tests_passed:
        print_success("\nAll tests passed! ✨")
        return 0
    else:
        print_error("\nSome tests failed. See above for details.")
        print_info("\nTroubleshooting tips:")
        print_info("1. Ensure you're in the virtual environment: source .venv/bin/activate")
        print_info("2. Run 'uv sync' in each environment directory")
        print_info("3. Install packages in editable mode: uv pip install -e environments/sv-env-*")
        print_info("4. Restart your IDE/language server")
        print_info("5. Run with --verbose flag for detailed error messages")
        return 1


if __name__ == "__main__":
    sys.exit(main())
