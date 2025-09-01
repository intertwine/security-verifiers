#!/usr/bin/env python
"""Run all environment tests separately to avoid import conflicts."""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run tests for each environment separately."""
    root = Path(__file__).parent
    environments = sorted(root.glob("environments/*/tests"))
    
    all_passed = True
    results = []
    
    for env_test_dir in environments:
        env_name = env_test_dir.parent.name
        test_file = env_test_dir / "test_main.py"
        
        if not test_file.exists():
            continue
            
        print(f"\n{'='*60}")
        print(f"Testing {env_name}...")
        print('='*60)
        
        result = subprocess.run(
            ["uv", "run", "pytest", str(test_file), "-q"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {env_name}: All tests passed")
            results.append((env_name, "PASSED"))
        else:
            print(f"❌ {env_name}: Some tests failed")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            all_passed = False
            results.append((env_name, "FAILED"))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for env_name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {env_name}: {status}")
    
    if all_passed:
        print("\n🎉 All environment tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed. See output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())