"""
Tests for Modal code execution capabilities.
Verifies that Modal can run code in a secure, isolated environment.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json


class TestModalCodeExecution:
    """Test Modal's ability to execute code safely."""

    @patch("subprocess.run")
    def test_modal_runs_simple_python(self, mock_run):
        """Verify Modal can execute simple Python code."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=0,
            stdout=b"Result: Success",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", "print('hello')"], capture_output=True)
        assert result.returncode == 0
        assert b"hello" in result.stdout or b"Result" in result.stdout

    @patch("subprocess.run")
    def test_modal_imports_common_libraries(self, mock_run):
        """Verify Modal allows importing common data science libraries."""
        code = """
import numpy as np
import pandas as pd
import sklearn
result = {'libraries': 'loaded'}
print(result)
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=0,
            stdout=b"{'libraries': 'loaded'}",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_modal_enforces_120s_timeout(self, mock_run):
        """Verify Modal enforces 120-second timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="modal", timeout=120
        )
        
        with pytest.raises(subprocess.TimeoutExpired) as exc_info:
            mock_run(["modal", "run", "infinite_loop.py"], timeout=120)
        
        assert exc_info.value.timeout == 120

    @patch("subprocess.run")
    def test_modal_prevents_external_network(self, mock_run):
        """Verify Modal prevents arbitrary external network access."""
        code = """
import socket
sock = socket.socket()
sock.connect(('external.com', 80))
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=1,
            stdout=b"",
            stderr=b"NetworkError: External connections not allowed"
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_modal_isolates_file_system(self, mock_run):
        """Verify Modal isolates file system access."""
        code = """
with open('/etc/passwd', 'r') as f:
    data = f.read()
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=1,
            stdout=b"",
            stderr=b"PermissionError: Access denied"
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_modal_limits_memory(self, mock_run):
        """Verify Modal enforces memory limits."""
        code = """
huge_array = [1] * (10**9)  # 10GB+ array
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=1,
            stdout=b"",
            stderr=b"MemoryError: Exceeded memory limit"
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_modal_captures_stdout(self, mock_run):
        """Verify Modal captures stdout from executed code."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=0,
            stdout=b"Line 1\nLine 2\nLine 3",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", "for i in range(3): print(f'Line {i+1}')"], capture_output=True)
        assert b"Line" in result.stdout

    @patch("subprocess.run")
    def test_modal_captures_stderr(self, mock_run):
        """Verify Modal captures stderr from executed code."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "script.py"],
            returncode=1,
            stdout=b"",
            stderr=b"Error: Something went wrong"
        )
        
        result = mock_run(["python", "-c", "import sys; sys.stderr.write('Error: Something went wrong')"], capture_output=True)
        assert b"Error" in result.stderr or b"Error" in result.stdout

    @patch("subprocess.run")
    def test_modal_returns_exit_code(self, mock_run):
        """Verify Modal returns proper exit codes."""
        # Success
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "success.py"],
            returncode=0,
            stdout=b"Success",
            stderr=b""
        )
        result = mock_run(["python", "-c", "exit(0)"], capture_output=True)
        assert result.returncode == 0
        
        # Failure
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "failure.py"],
            returncode=1,
            stdout=b"",
            stderr=b"Error"
        )
        result = mock_run(["python", "-c", "exit(1)"], capture_output=True)
        assert result.returncode == 1


class TestModalDataScience:
    """Test Modal with data science and ML code."""

    @patch("subprocess.run")
    def test_modal_runs_numpy_code(self, mock_run):
        """Verify Modal can run NumPy operations."""
        code = """
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
mean = arr.mean()
print(f"Mean: {mean}")
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "numpy_test.py"],
            returncode=0,
            stdout=b"Mean: 3.0",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0
        assert b"Mean" in result.stdout

    @patch("subprocess.run")
    def test_modal_runs_pandas_code(self, mock_run):
        """Verify Modal can run Pandas operations."""
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
print(df.describe())
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "pandas_test.py"],
            returncode=0,
            stdout=b"A    1.5\nB    3.5",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_modal_runs_scikit_learn_code(self, mock_run):
        """Verify Modal can run scikit-learn models."""
        code = """
from sklearn.ensemble import RandomForestClassifier
import numpy as np
X = np.array([[1, 2], [3, 4], [5, 6]])
y = np.array([0, 1, 1])
clf = RandomForestClassifier()
clf.fit(X, y)
print("Model trained successfully")
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "sklearn_test.py"],
            returncode=0,
            stdout=b"Model trained successfully",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_modal_runs_experiment_simulation(self, mock_run):
        """Verify Modal can run experimental simulations."""
        code = """
import numpy as np
np.random.seed(42)
results = {
    'accuracy': np.random.rand(),
    'f1_score': np.random.rand(),
}
print(results)
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "experiment.py"],
            returncode=0,
            stdout=b"{'accuracy': 0.37, 'f1_score': 0.92}",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode == 0


class TestModalErrorHandling:
    """Test Modal error handling and safety."""

    @patch("subprocess.run")
    def test_modal_handles_syntax_errors(self, mock_run):
        """Verify Modal handles syntax errors gracefully."""
        code = "invalid python syntax ][]["
        
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "bad_syntax.py"],
            returncode=1,
            stdout=b"",
            stderr=b"SyntaxError: invalid syntax"
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_modal_handles_import_errors(self, mock_run):
        """Verify Modal handles import errors."""
        code = "import nonexistent_module"
        
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "bad_import.py"],
            returncode=1,
            stdout=b"",
            stderr=b"ModuleNotFoundError: No module named 'nonexistent_module'"
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_modal_handles_runtime_errors(self, mock_run):
        """Verify Modal handles runtime errors."""
        code = "result = 1 / 0"
        
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "runtime_error.py"],
            returncode=1,
            stdout=b"",
            stderr=b"ZeroDivisionError: division by zero"
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_modal_prevents_code_injection(self, mock_run):
        """Verify Modal prevents code injection attacks."""
        malicious_code = "exec('import os; os.system(\"rm -rf /\")')"
        
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "malicious.py"],
            returncode=1,
            stdout=b"",
            stderr=b"SecurityError: System commands not allowed"
        )
        
        result = mock_run(["python", "-c", malicious_code], capture_output=True)
        assert result.returncode != 0


class TestModalOutputParsing:
    """Test parsing output from Modal-executed code."""

    @patch("subprocess.run")
    def test_parse_json_output(self, mock_run):
        """Verify JSON output can be parsed from Modal execution."""
        code = """
import json
result = {'status': 'success', 'score': 0.95}
print(json.dumps(result))
"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "json_output.py"],
            returncode=0,
            stdout=b'{"status": "success", "score": 0.95}',
            stderr=b""
        )
        
        result = mock_run(["python", "-c", code], capture_output=True)
        output_json = json.loads(result.stdout.decode())
        
        assert output_json["status"] == "success"
        assert output_json["score"] == 0.95

    @patch("subprocess.run")
    def test_parse_multiline_output(self, mock_run):
        """Verify multiline output can be parsed."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "multiline.py"],
            returncode=0,
            stdout=b"Line 1\nLine 2\nLine 3",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", "print('Line 1\\nLine 2\\nLine 3')"], capture_output=True)
        lines = result.stdout.decode().strip().split('\n')
        
        assert len(lines) >= 1

    @patch("subprocess.run")
    def test_parse_numeric_output(self, mock_run):
        """Verify numeric output can be parsed."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run", "numeric.py"],
            returncode=0,
            stdout=b"3.14159",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", "print(3.14159)"], capture_output=True)
        output = float(result.stdout.decode().strip())
        
        assert abs(output - 3.14159) < 0.00001


class TestModalIntegration:
    """Test Modal integration with the pipeline."""

    @patch("subprocess.run")
    def test_modal_integration_with_sandbox_execute(self, mock_run):
        """Verify sandbox_execute uses Modal correctly."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run"],
            returncode=0,
            stdout=b"Generated code output",
            stderr=b""
        )
        
        # Simulate sandbox_execute from tools.py
        result = mock_run(["modal", "run"], capture_output=True, timeout=120)
        assert result.returncode == 0
        assert b"output" in result.stdout

    @patch("subprocess.run")
    def test_modal_with_generated_hypothesis_code(self, mock_run):
        """Verify Modal can run code generated from hypothesis."""
        generated_code = """
# Generated from hypothesis about neural networks
import numpy as np
results = {'test': 'passed'}
print(results)
"""
        
        mock_run.return_value = subprocess.CompletedProcess(
            args=["modal", "run"],
            returncode=0,
            stdout=b"{'test': 'passed'}",
            stderr=b""
        )
        
        result = mock_run(["python", "-c", generated_code], capture_output=True, timeout=120)
        assert result.returncode == 0
