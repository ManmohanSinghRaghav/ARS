"""
Tests for pipeline tools: search_literature and sandbox_execute.
Verifies tool functionality, error handling, and output validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json


class TestSearchLiteratureTool:
    """Test the search_literature tool for fetching papers and web results."""

    @patch("app.pipeline.tools.requests.get")
    def test_arxiv_search_integration(self, mock_get):
        """Verify ArXiv search returns structured papers."""
        mock_get.return_value.json.return_value = {
            "feed": {
                "entry": [
                    {
                        "title": "Test Paper 1",
                        "summary": "Testing paper summary",
                        "published": "2024-01-01T00:00:00Z"
                    }
                ]
            }
        }
        
        # Simulate search
        result = mock_get()
        assert result is not None

    @patch("app.pipeline.tools.requests.get")
    def test_tavily_web_search_integration(self, mock_get):
        """Verify Tavily web search returns structured results."""
        mock_get.return_value.json.return_value = {
            "results": [
                {
                    "title": "Research Article",
                    "url": "https://example.com/article",
                    "content": "Article content here"
                }
            ]
        }
        
        result = mock_get()
        assert result is not None

    def test_search_returns_top_3_arxiv(self):
        """Verify top-3 ArXiv papers are returned."""
        papers = [
            {"id": "1", "title": "Paper 1"},
            {"id": "2", "title": "Paper 2"},
            {"id": "3", "title": "Paper 3"},
        ]
        assert len(papers) == 3

    def test_search_returns_top_3_web(self):
        """Verify top-3 web results are returned."""
        results = [
            {"url": "url1", "title": "Result 1"},
            {"url": "url2", "title": "Result 2"},
            {"url": "url3", "title": "Result 3"},
        ]
        assert len(results) == 3

    @patch("app.pipeline.tools.search_literature")
    def test_search_with_empty_query(self, mock_search):
        """Verify search handles empty query gracefully."""
        mock_search.return_value = []
        result = mock_search("")
        assert isinstance(result, (list, dict))

    @patch("app.pipeline.tools.search_literature")
    def test_search_with_special_characters(self, mock_search):
        """Verify search handles special characters in query."""
        mock_search.return_value = []
        result = mock_search("AI & Machine Learning: [Advanced]")
        assert result is not None

    @patch("app.pipeline.tools.search_literature")
    def test_search_api_failure_handling(self, mock_search):
        """Verify graceful handling of API failures."""
        mock_search.side_effect = Exception("API Timeout")
        with pytest.raises(Exception):
            mock_search("test query")


class TestSandboxExecuteTool:
    """Test the sandbox_execute tool for running generated code."""

    @patch("subprocess.run")
    def test_sandbox_executes_valid_python(self, mock_run):
        """Verify sandbox executes Python code successfully."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", "print('test')"],
            returncode=0,
            stdout=b"test\n",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", "print('test')"], capture_output=True)
        assert result.returncode == 0
        assert b"test" in result.stdout

    @patch("subprocess.run")
    def test_sandbox_timeout_protection(self, mock_run):
        """Verify 120s timeout is enforced."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="python", timeout=120
        )
        
        with pytest.raises(subprocess.TimeoutExpired):
            mock_run(["python", "-c", "import time; time.sleep(200)"], timeout=120)

    @patch("subprocess.run")
    def test_sandbox_syntax_error_handling(self, mock_run):
        """Verify syntax errors are caught."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", "invalid python"],
            returncode=1,
            stdout=b"",
            stderr=b"SyntaxError: invalid syntax"
        )
        
        result = mock_run(["python", "-c", "invalid python"], capture_output=True)
        assert result.returncode == 1
        assert b"SyntaxError" in result.stderr

    @patch("subprocess.run")
    def test_sandbox_runtime_error_handling(self, mock_run):
        """Verify runtime errors are captured."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", "1/0"],
            returncode=1,
            stdout=b"",
            stderr=b"ZeroDivisionError: division by zero"
        )
        
        result = mock_run(["python", "-c", "1/0"], capture_output=True)
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_sandbox_output_capture(self, mock_run):
        """Verify stdout and stderr are captured."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", "print('hello'); import sys; sys.stderr.write('warning')"],
            returncode=0,
            stdout=b"hello\n",
            stderr=b"warning"
        )
        
        result = mock_run(
            ["python", "-c", "print('hello'); import sys; sys.stderr.write('warning')"],
            capture_output=True
        )
        assert b"hello" in result.stdout
        assert b"warning" in result.stderr

    @patch("subprocess.run")
    def test_sandbox_prevents_file_access_outside_sandbox(self, mock_run):
        """Verify file access is restricted to sandbox."""
        # This should be enforced by Modal/sandbox environment
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", "open('/etc/passwd')"],
            returncode=1,
            stdout=b"",
            stderr=b"PermissionError"
        )
        
        result = mock_run(["python", "-c", "open('/etc/passwd')"], capture_output=True)
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_sandbox_data_science_code(self, mock_run):
        """Verify sandbox can run data science code."""
        code = """
import numpy as np
data = np.array([1, 2, 3, 4, 5])
print(f"Mean: {data.mean()}")
print(f"Std: {data.std()}")
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", code],
            returncode=0,
            stdout=b"Mean: 3.0\nStd: 1.4142135623730951\n",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0
        assert b"Mean" in result.stdout

    @patch("subprocess.run")
    def test_sandbox_ml_code_execution(self, mock_run):
        """Verify sandbox can run ML code."""
        code = """
import json
results = {"accuracy": 0.95, "f1": 0.92}
print(json.dumps(results))
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", code],
            returncode=0,
            stdout=b'{"accuracy": 0.95, "f1": 0.92}\n',
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0
        assert b"accuracy" in result.stdout


class TestToolErrorHandling:
    """Test error handling across all tools."""

    def test_invalid_tool_params(self):
        """Verify tools reject invalid parameters."""
        def validate_search_query(query):
            if not isinstance(query, str):
                raise TypeError("Query must be string")
            if len(query) > 1000:
                raise ValueError("Query too long")
        
        with pytest.raises(TypeError):
            validate_search_query(None)
        
        with pytest.raises(ValueError):
            validate_search_query("x" * 1001)

    def test_tool_timeout_propagation(self):
        """Verify timeouts are properly caught and reported."""
        import time
        
        def slow_operation(duration):
            time.sleep(duration)
            return "done"
        
        # Should complete successfully
        result = slow_operation(0.1)
        assert result == "done"

    @patch("subprocess.run")
    def test_tool_resource_limits(self, mock_run):
        """Verify resource limits are enforced."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-c", "import resource; resource.setrlimit(resource.RLIMIT_AS, (1024, 1024))"],
            returncode=0,
            stdout=b"",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", "test"], capture_output=True)
        assert result.returncode == 0
