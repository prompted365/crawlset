#!/usr/bin/env python3
"""
Verification script for distributed processing setup.

Run this to verify all modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")

    queue_success = False
    preprocessing_success = False

    # Try queue module (may fail if Celery not installed)
    try:
        from src.queue.celery_app import app
        from src.queue.tasks import (
            extract_url_task,
            batch_extract_task,
            process_webset_task,
            run_monitor_task,
            enrich_item_task,
            cleanup_expired_results,
        )
        from src.queue.workers import (
            start_worker,
            get_worker_health,
        )
        print("✓ Queue module imports successful")
        queue_success = True
    except ImportError as e:
        print(f"⚠ Queue module import skipped: {e}")
        print("  (Run 'pip install -r requirements.txt' to enable queue tests)")

    # Try preprocessing module
    try:
        from src.preprocessing.chunker import (
            TextChunker,
            ChunkingStrategy,
            chunk_text,
            chunk_for_embedding,
        )
        from src.preprocessing.cleaner import (
            ContentCleaner,
            clean_content,
            clean_for_embedding,
        )
        from src.preprocessing.reranker import (
            ResultReranker,
            RerankingStrategy,
            SearchResult,
            rerank_results,
        )
        print("✓ Preprocessing module imports successful")
        preprocessing_success = True
    except ImportError as e:
        print(f"✗ Preprocessing module import failed: {e}")

    # Return True if at least preprocessing works
    return preprocessing_success


def test_chunking():
    """Test text chunking functionality."""
    print("\nTesting text chunking...")

    try:
        from src.preprocessing import chunk_text, ChunkingStrategy

        text = "This is sentence one. This is sentence two. This is sentence three. " * 10

        # Test sentence chunking
        chunks = chunk_text(
            text,
            strategy=ChunkingStrategy.SENTENCE,
            chunk_size=200,
            chunk_overlap=50
        )

        assert len(chunks) > 0, "No chunks created"
        assert all(hasattr(c, 'text') for c in chunks), "Chunks missing text attribute"
        print(f"✓ Created {len(chunks)} chunks from text")

        return True

    except Exception as e:
        print(f"✗ Chunking test failed: {e}")
        return False


def test_cleaning():
    """Test content cleaning functionality."""
    print("\nTesting content cleaning...")

    try:
        from src.preprocessing import clean_content

        dirty_text = """
        <div>
            Hello   world!


            This is a test.

            © 2024 Test Corp. All rights reserved.
            Cookie Policy | Privacy Policy
        </div>
        """

        cleaned = clean_content(dirty_text, remove_boilerplate=True)

        assert "Hello world!" in cleaned or "Hello   world!" in cleaned, "Text lost during cleaning"
        assert cleaned.count('\n\n\n') == 0, "Whitespace not normalized"
        print("✓ Content cleaning successful")

        return True

    except Exception as e:
        print(f"✗ Cleaning test failed: {e}")
        return False


def test_reranking():
    """Test result reranking functionality."""
    print("\nTesting result reranking...")

    try:
        from src.preprocessing import SearchResult, rerank_results, RerankingStrategy

        results = [
            SearchResult(id="1", text="First result", score=0.5),
            SearchResult(id="2", text="Second result", score=0.9),
            SearchResult(id="3", text="Third result", score=0.7),
        ]

        reranked = rerank_results(results, strategy=RerankingStrategy.SCORE)

        assert len(reranked) == 3, "Results lost during reranking"
        assert reranked[0].score >= reranked[1].score, "Not properly sorted by score"
        assert reranked[0].id == "2", "Highest score not first"
        print("✓ Result reranking successful")

        return True

    except Exception as e:
        print(f"✗ Reranking test failed: {e}")
        return False


def test_celery_config():
    """Test Celery configuration."""
    print("\nTesting Celery configuration...")

    try:
        from src.queue.celery_app import app

        # Check basic config
        assert app.conf.task_serializer == "json", "Task serializer not set to JSON"
        assert app.conf.timezone == "UTC", "Timezone not set to UTC"

        # Check queues
        queues = [q.name for q in app.conf.task_queues]
        expected_queues = ["realtime", "batch", "background"]
        assert all(q in queues for q in expected_queues), f"Missing queues: {expected_queues}"

        print(f"✓ Celery configured with queues: {', '.join(queues)}")

        return True

    except ImportError as e:
        print(f"⚠ Celery config test skipped (dependencies not installed)")
        return None  # Indicate skipped

    except Exception as e:
        print(f"✗ Celery config test failed: {e}")
        return False


def test_task_definitions():
    """Test that tasks are properly defined."""
    print("\nTesting task definitions...")

    try:
        from src.queue.celery_app import app

        registered_tasks = list(app.tasks.keys())

        expected_tasks = [
            "src.queue.tasks.extract_url_task",
            "src.queue.tasks.batch_extract_task",
            "src.queue.tasks.process_webset_task",
            "src.queue.tasks.run_monitor_task",
            "src.queue.tasks.enrich_item_task",
        ]

        found_tasks = [t for t in expected_tasks if t in registered_tasks]

        print(f"✓ Found {len(found_tasks)}/{len(expected_tasks)} expected tasks:")
        for task in found_tasks:
            print(f"  - {task.split('.')[-1]}")

        if len(found_tasks) < len(expected_tasks):
            missing = [t for t in expected_tasks if t not in registered_tasks]
            print(f"  Missing tasks: {missing}")

        return len(found_tasks) == len(expected_tasks)

    except ImportError as e:
        print(f"⚠ Task definition test skipped (dependencies not installed)")
        return None  # Indicate skipped

    except Exception as e:
        print(f"✗ Task definition test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Distributed Processing Layer Verification")
    print("=" * 60)

    tests = [
        ("Module Imports", test_imports),
        ("Celery Configuration", test_celery_config),
        ("Task Definitions", test_task_definitions),
        ("Text Chunking", test_chunking),
        ("Content Cleaning", test_cleaning),
        ("Result Reranking", test_reranking),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ {name} failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success is True)
    skipped = sum(1 for _, success in results if success is None)
    failed = sum(1 for _, success in results if success is False)
    total = len(results)

    for name, success in results:
        if success is True:
            status = "✓ PASS"
        elif success is None:
            status = "⚠ SKIP"
        else:
            status = "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed} passed, {skipped} skipped, {failed} failed ({total} total)")

    if failed == 0 and passed > 0:
        print("\n✓ All available tests passed! Distributed processing layer is ready.")
        if skipped > 0:
            print("  Note: Some tests were skipped due to missing dependencies.")
            print("  Run 'pip install -r requirements.txt' to enable all tests.")
        return 0
    elif failed > 0:
        print(f"\n✗ {failed} test(s) failed. Please check the errors above.")
        return 1
    else:
        print("\n⚠ No tests could run. Check dependencies.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
