#!/usr/bin/env python3
"""
Architecture Verification Script

Checks that all question detection components are properly installed
and ready to run.
"""

import sys
import subprocess
import importlib.util


def check_module(name, import_name=None):
    """Check if a Python module is installed"""
    check_name = import_name or name
    spec = importlib.util.find_spec(check_name)
    if spec is None:
        print(f"❌ {name} NOT installed")
        return False
    print(f"✅ {name} installed")
    return True


def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379)
        client.ping()
        print("✅ Redis running")
        return True
    except Exception as e:
        print(f"❌ Redis not running: {e}")
        return False


def check_file(path):
    """Check if file exists"""
    from pathlib import Path
    if Path(path).exists():
        print(f"✅ {path}")
        return True
    print(f"❌ {path} missing")
    return False


def main():
    print("\n" + "="*60)
    print("Question Detection - Architecture Verification")
    print("="*60 + "\n")
    
    checks = {
        "Python Modules": [
            ("Transformers", "transformers"),
            ("PyTorch", "torch"),
            ("Redis", "redis"),
            ("AsyncIO", "asyncio"),
        ],
        "Services": [
            ("services/question_detector.py", "backend/app/services/question_detector.py"),
            ("services/llm_responder.py", "backend/app/services/llm_responder.py"),
            ("services/meeting_session.py", "backend/app/services/meeting_session.py"),
            ("services/persistence.py", "backend/app/services/persistence.py"),
        ],
        "Documentation": [
            ("QUESTION_DETECTION.md", "backend/QUESTION_DETECTION.md"),
            ("IMPLEMENTATION_SUMMARY.md", "backend/IMPLEMENTATION_SUMMARY.md"),
            ("QUICK_START.md", "backend/QUICK_START.md"),
        ],
        "Demo": [
            ("demo_question_detection.py", "backend/demo_question_detection.py"),
        ]
    }
    
    all_passed = True
    
    # Check modules
    print("📦 Python Modules:")
    for name, import_name in checks["Python Modules"]:
        if not check_module(name, import_name):
            all_passed = False
    
    # Check Redis
    print("\n🗄️  Redis Service:")
    if not check_redis():
        all_passed = False
    
    # Check files
    print("\n📁 Service Files:")
    for name, path in checks["Services"]:
        if not check_file(path):
            all_passed = False
    
    print("\n📚 Documentation:")
    for name, path in checks["Documentation"]:
        if not check_file(path):
            all_passed = False
    
    print("\n🎮 Demo:")
    for name, path in checks["Demo"]:
        if not check_file(path):
            all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✅ All checks passed! Ready to run.")
        print("\nNext steps:")
        print("1. Start Redis: redis-server")
        print("2. Run app: python -m uvicorn app.main:app")
        print("3. Check QUICK_START.md for testing")
    else:
        print("⚠️  Some checks failed. Please review above.")
        print("\nTroubleshooting:")
        print("1. Install missing modules: pip install -r requirements.txt")
        print("2. Start Redis: redis-server")
        print("3. Verify all files were created")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
