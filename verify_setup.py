"""Verify that the Better Coverage setup is correct."""

import sys
from pathlib import Path


def verify_imports():
    """Verify all required imports work."""
    print("🔍 Verifying imports...")
    
    try:
        import anthropic
        print("  ✅ anthropic")
    except ImportError as e:
        print(f"  ❌ anthropic: {e}")
        return False
    
    try:
        import pydantic
        print("  ✅ pydantic")
    except ImportError as e:
        print(f"  ❌ pydantic: {e}")
        return False
    
    try:
        import dotenv
        print("  ✅ python-dotenv")
    except ImportError as e:
        print(f"  ❌ python-dotenv: {e}")
        return False
    
    try:
        import claude_agent_sdk
        print("  ✅ claude-agent-sdk")
    except ImportError as e:
        print(f"  ❌ claude-agent-sdk: {e}")
        return False
    
    return True


def verify_project_structure():
    """Verify project structure is correct."""
    print("\n📁 Verifying project structure...")
    
    required_paths = [
        "app/__init__.py",
        "app/models/__init__.py",
        "app/models/contract.py",
        "app/services/__init__.py",
        "app/services/contract_discovery/__init__.py",
        "app/services/contract_discovery/agent.py",
        "app/services/contract_discovery/prompts.py",
        "app/services/llm_driver/__init__.py",
        "app/services/llm_driver/anthropic_handler.py",
        "app/services/llm_driver/policies.py",
        "run_discovery.py",
        "requirements.txt",
        ".env.example",
    ]
    
    all_exist = True
    for path_str in required_paths:
        path = Path(path_str)
        if path.exists():
            print(f"  ✅ {path_str}")
        else:
            print(f"  ❌ {path_str} (missing)")
            all_exist = False
    
    return all_exist


def verify_env():
    """Verify environment setup."""
    print("\n🔐 Verifying environment...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("  ⚠️  .env file not found (copy from .env.example)")
        return False
    
    print("  ✅ .env file exists")
    
    # Check if API key is set
    with env_file.open() as f:
        content = f.read()
        if "ANTHROPIC_API_KEY" in content and "your_api_key_here" not in content:
            print("  ✅ ANTHROPIC_API_KEY appears to be set")
            return True
        else:
            print("  ⚠️  ANTHROPIC_API_KEY not set in .env")
            return False


def verify_models():
    """Verify models can be imported."""
    print("\n📦 Verifying models...")
    
    try:
        from app.models.contract import (
            Contract,
            ContractDiscoveryResult,
            ContractSeverity,
            ContractType,
        )
        print("  ✅ Contract models")
        
        # Quick validation
        from app.models.contract import CodeLocation
        loc = CodeLocation(
            file_path="test.py",
            line_start=1,
            line_end=10,
            code_snippet="test code"
        )
        print("  ✅ Models instantiate correctly")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def verify_agent():
    """Verify agent can be imported."""
    print("\n🤖 Verifying agent...")
    
    try:
        from app.services.contract_discovery import ContractDiscoveryAgent
        print("  ✅ ContractDiscoveryAgent imports")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Run all verifications."""
    print("=" * 80)
    print("BETTER COVERAGE - SETUP VERIFICATION")
    print("=" * 80)
    
    results = []
    
    results.append(("Imports", verify_imports()))
    results.append(("Project Structure", verify_project_structure()))
    results.append(("Environment", verify_env()))
    results.append(("Models", verify_models()))
    results.append(("Agent", verify_agent()))
    
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    
    if all_passed:
        print("✅ All checks passed! You're ready to run contract discovery.")
        print("\nNext steps:")
        print("  python run_discovery.py merit-travelops-demo/app")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Copy .env.example to .env and add your ANTHROPIC_API_KEY")
        return 1


if __name__ == "__main__":
    sys.exit(main())
