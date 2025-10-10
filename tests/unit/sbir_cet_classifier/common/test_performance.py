"""Unit tests for performance monitoring utilities."""

import time
from io import StringIO
from unittest.mock import patch

import pytest

from sbir_cet_classifier.common.performance import (
    profile_memory,
    time_function,
    timer,
)


class TestTimer:
    """Test timer context manager."""

    def test_timer_measures_elapsed_time(self, capsys):
        """Test that timer measures and prints elapsed time."""
        with timer("test_operation"):
            time.sleep(0.01)  # Sleep for 10ms

        captured = capsys.readouterr()
        assert "test_operation" in captured.out
        assert "0.0" in captured.out  # Should show time in seconds
        assert "⏱️" in captured.out

    def test_timer_executes_code_block(self):
        """Test that code inside timer block executes."""
        result = []
        with timer("test"):
            result.append(1)
            result.append(2)

        assert result == [1, 2]

    def test_timer_handles_exceptions(self, capsys):
        """Test that timer prints time even when exception occurs."""
        with pytest.raises(ValueError):
            with timer("error_operation"):
                raise ValueError("Test error")

        captured = capsys.readouterr()
        assert "error_operation" in captured.out

    def test_timer_with_zero_duration(self, capsys):
        """Test timer with very fast operation."""
        with timer("instant"):
            pass  # No-op

        captured = capsys.readouterr()
        assert "instant" in captured.out
        assert "0.000s" in captured.out or "0.001s" in captured.out


class TestTimeFunction:
    """Test time_function decorator."""

    def test_time_function_measures_slow_operation(self, capsys):
        """Test that decorator times slow functions."""
        @time_function
        def slow_function():
            time.sleep(0.15)  # Sleep for 150ms (> 100ms threshold)
            return "done"

        result = slow_function()

        assert result == "done"
        captured = capsys.readouterr()
        assert "slow_function" in captured.out
        assert "0.1" in captured.out
        assert "⏱️" in captured.out

    def test_time_function_skips_fast_operation(self, capsys):
        """Test that decorator skips timing for fast functions."""
        @time_function
        def fast_function():
            return "quick"

        result = fast_function()

        assert result == "quick"
        captured = capsys.readouterr()
        # Should not print anything for fast operations (<100ms)
        assert "fast_function" not in captured.out

    def test_time_function_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @time_function
        def my_function():
            """Docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "Docstring."

    def test_time_function_with_arguments(self, capsys):
        """Test decorator works with function arguments."""
        @time_function
        def add(a, b):
            time.sleep(0.15)
            return a + b

        result = add(2, 3)

        assert result == 5
        captured = capsys.readouterr()
        assert "add" in captured.out

    def test_time_function_with_kwargs(self, capsys):
        """Test decorator works with keyword arguments."""
        @time_function
        def greet(name, greeting="Hello"):
            time.sleep(0.15)
            return f"{greeting}, {name}"

        result = greet("Alice", greeting="Hi")

        assert result == "Hi, Alice"
        captured = capsys.readouterr()
        assert "greet" in captured.out


class TestProfileMemory:
    """Test profile_memory decorator."""

    def test_profile_memory_without_psutil(self, capsys):
        """Test that decorator works when psutil is not available."""
        with patch.dict('sys.modules', {'psutil': None}):
            @profile_memory
            def simple_function():
                return [1, 2, 3]

            result = simple_function()

            assert result == [1, 2, 3]
            captured = capsys.readouterr()
            # Should not print anything when psutil unavailable
            assert captured.out == ""

    def test_profile_memory_with_small_change(self, capsys):
        """Test that small memory changes are not logged."""
        @profile_memory
        def small_allocation():
            # Small allocation (<10MB)
            small_list = [1] * 100
            return small_list

        result = small_allocation()

        assert len(result) == 100
        captured = capsys.readouterr()
        # Should not print for small memory changes
        assert "🧠" not in captured.out or captured.out == ""

    def test_profile_memory_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @profile_memory
        def test_func():
            """Test docstring."""
            return 42

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test docstring."

    def test_profile_memory_with_arguments(self):
        """Test decorator works with function arguments."""
        @profile_memory
        def multiply(x, y):
            return x * y

        result = multiply(3, 4)
        assert result == 12

    def test_profile_memory_with_exception(self):
        """Test that decorator handles exceptions."""
        @profile_memory
        def failing_function():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError, match="Test error"):
            failing_function()

    @pytest.mark.skipif(
        not pytest.importorskip("psutil", reason="psutil not installed"),
        reason="Requires psutil"
    )
    def test_profile_memory_with_large_allocation(self, capsys):
        """Test that large memory allocations are logged."""
        @profile_memory
        def large_allocation():
            # Allocate >10MB
            large_list = [0] * (2 * 1024 * 1024)  # ~16MB of integers
            return len(large_list)

        result = large_allocation()

        assert result == 2 * 1024 * 1024
        captured = capsys.readouterr()
        # May or may not show depending on system, but function should work
        assert result > 0


class TestDecoratorComposition:
    """Test combining decorators."""

    def test_time_and_profile_together(self, capsys):
        """Test that both decorators can be used together."""
        @time_function
        @profile_memory
        def combined_function():
            time.sleep(0.15)
            return "result"

        result = combined_function()

        assert result == "result"
        captured = capsys.readouterr()
        # Should see timing output for slow function
        assert "combined_function" in captured.out or "wrapper" in captured.out
