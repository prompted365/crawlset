#!/usr/bin/env python3
"""
Verification script for backend infrastructure setup.

This script validates that all components are properly created and importable.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def verify_imports():
    """Verify all core modules can be imported."""
    print("Verifying imports...")

    try:
        # Database imports
        from src.database import (
            Base,
            ExtractionJob,
            Monitor,
            MonitorRun,
            Webset,
            WebsetItem,
            DatabaseManager,
            get_db_manager,
            get_db_session,
            init_database,
        )
        print("✓ Database models and connection imported successfully")

        # Schema imports
        from src.api.schemas import (
            WebsetCreate,
            WebsetUpdate,
            WebsetResponse,
            WebsetItemCreate,
            WebsetItemResponse,
            MonitorCreate,
            MonitorUpdate,
            MonitorResponse,
            MonitorRunCreate,
            MonitorRunResponse,
            ExtractionJobCreate,
            ExtractionJobUpdate,
            ExtractionJobResponse,
        )
        print("✓ API schemas imported successfully")

        # Config imports
        from src.config import get_settings, Settings
        print("✓ Configuration management imported successfully")

        # Main app import
        from src.api.main import app
        print("✓ FastAPI application imported successfully")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_settings():
    """Verify settings can be loaded."""
    print("\nVerifying settings...")

    try:
        from src.config import get_settings

        settings = get_settings()
        print(f"✓ Settings loaded successfully")
        print(f"  - Database URL: {settings.database_url}")
        print(f"  - Port: {settings.port}")
        print(f"  - CORS Origins: {settings.cors_origins}")
        print(f"  - Requesty Model: {settings.requesty_default_model}")

        return True
    except Exception as e:
        print(f"✗ Settings verification failed: {e}")
        return False


def verify_database_models():
    """Verify database models are properly configured."""
    print("\nVerifying database models...")

    try:
        from src.database.models import Base, Webset, WebsetItem, Monitor, MonitorRun, ExtractionJob

        # Check all models have proper tablenames
        models = [Webset, WebsetItem, Monitor, MonitorRun, ExtractionJob]
        for model in models:
            assert hasattr(model, "__tablename__"), f"{model.__name__} missing __tablename__"
            print(f"✓ {model.__name__} → {model.__tablename__}")

        # Check relationships
        assert hasattr(Webset, "items"), "Webset missing items relationship"
        assert hasattr(Webset, "monitors"), "Webset missing monitors relationship"
        assert hasattr(Monitor, "runs"), "Monitor missing runs relationship"
        print("✓ Model relationships configured correctly")

        return True
    except Exception as e:
        print(f"✗ Model verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schemas():
    """Verify Pydantic schemas are properly configured."""
    print("\nVerifying Pydantic schemas...")

    try:
        from src.api.schemas import (
            WebsetCreate,
            WebsetResponse,
            MonitorCreate,
            MonitorResponse,
            ExtractionJobCreate,
            ExtractionJobResponse,
        )

        # Test schema creation
        webset_data = {
            "id": "test-webset",
            "name": "Test Webset",
            "search_query": "test query",
            "entity_type": "podcast",
        }
        webset = WebsetCreate(**webset_data)
        print(f"✓ WebsetCreate schema validated: {webset.name}")

        monitor_data = {
            "id": "test-monitor",
            "webset_id": "test-webset",
            "cron_expression": "0 */6 * * *",
            "timezone": "UTC",
            "status": "enabled",
        }
        monitor = MonitorCreate(**monitor_data)
        print(f"✓ MonitorCreate schema validated: {monitor.cron_expression}")

        job_data = {
            "id": "test-job",
            "url": "https://example.com",
            "status": "pending",
        }
        job = ExtractionJobCreate(**job_data)
        print(f"✓ ExtractionJobCreate schema validated: {job.url}")

        return True
    except Exception as e:
        print(f"✗ Schema verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Backend Infrastructure Verification")
    print("=" * 60)

    results = []

    results.append(("Imports", verify_imports()))
    results.append(("Settings", verify_settings()))
    results.append(("Database Models", verify_database_models()))
    results.append(("Pydantic Schemas", verify_schemas()))

    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All verification tests passed!")
        print("\nNext steps:")
        print("1. Run the application: uvicorn src.api.main:app --reload")
        print("2. Access API docs: http://localhost:8080/docs")
        print("3. Check health: http://localhost:8080/health")
        return 0
    else:
        print("\n✗ Some verification tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
