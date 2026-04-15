# ARS Backend Testing Guide

This document provides comprehensive guidance on running, writing, and maintaining tests for the ARS backend.

## Overview

The test suite covers:
- ✅ **Agents**: Research pipeline agents (Researcher, Scientist, Critics, Writers)
- ✅ **Tools**: Search literature, sandbox code execution
- ✅ **Pipeline**: Orchestration, background execution, progress tracking
- ✅ **Integrations**: Redis caching, ChromaDB vector store, Firebase/Firestore
- ✅ **Modal**: Secure code execution environments
- ✅ **API Endpoints**: All FastAPI routes and error handling
- ✅ **Auth**: User authentication and authorization

## Quick Start

### 1. Install Test Dependencies

```bash
cd backend
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### 2. Run All Tests

```bash
# Run all tests with verbose output
pytest

# Run with coverage report
pytest --cov=app tests/

# Run specific test file
pytest tests/test_agents.py

# Run specific test class
pytest tests/test_agents.py::TestAgentCreation

# Run specific test
pytest tests/test_agents.py::TestAgentCreation::test_researcher_agent_creation
```

### 3. Run Tests by Category

```bash
# Unit tests only (fast, no external dependencies)
pytest -m unit

# Integration tests (require mocked external services)
pytest -m integration

# API endpoint tests
pytest -m api

# Agent tests
pytest -m agents

# Tool tests
pytest -m tools

# Modal execution tests
pytest -m modal

# Redis integration tests
pytest -m redis

# ChromaDB integration tests
pytest -m chromadb

# Firebase integration tests
pytest -m firebase
```

## Test Structure

```
backend/tests/
├── conftest.py                  # Shared fixtures and configuration
├── pytest.ini                   # Pytest configuration
├── test_agents.py              # Agent creation, delegation, progress
├── test_tools.py               # Search literature, sandbox execution
├── test_pipeline_runner.py     # Pipeline initialization, background execution
├── test_integrations.py        # Redis, ChromaDB, Firebase tests
├── test_modal.py               # Modal code execution tests
├── test_api_endpoints.py       # All FastAPI endpoint tests
└── test_api.py                 # Existing API tests
```

## Test Categories

### 1. Agent Tests (`test_agents.py`)

Tests for CrewAI agents and their orchestration.

```python
pytest -m agents
pytest tests/test_agents.py::TestAgentCreation
pytest tests/test_agents.py::TestAgentOutputValidation
```

**Covers:**
- Agent initialization and configuration
- Agent hierarchy and delegation
- Output validation (hypothesis, code, paper)
- Error handling
- Progress tracking

### 2. Tool Tests (`test_tools.py`)

Tests for pipeline tools: search_literature and sandbox_execute.

```python
pytest -m tools
pytest tests/test_tools.py::TestSearchLiteratureTool
pytest tests/test_tools.py::TestSandboxExecuteTool
```

**Covers:**
- ArXiv paper search (top-3)
- Tavily web search (top-3)
- Sandbox code execution
- 120-second timeout enforcement
- Error handling (syntax, runtime, import errors)
- Data science code execution
- Security (file access, network isolation)

### 3. Pipeline Tests (`test_pipeline_runner.py`)

Tests for pipeline execution and result persistence.

```python
pytest -m pipeline
pytest tests/test_pipeline_runner.py::TestPipelineInitialization
pytest tests/test_pipeline_runner.py::TestBackgroundExecution
```

**Covers:**
- Run record creation
- Background thread execution
- Firestore persistence
- Error handling
- Input validation
- Progress tracking

### 4. Integration Tests (`test_integrations.py`)

Tests for external service integrations.

```python
pytest -m integration
pytest -m redis
pytest -m chromadb
pytest -m firebase
```

**Covers:**
- **Redis:**
  - Connection and ping
  - Cache get/set
  - Cache expiration
  - LLM prompt caching
  - Fallback handling

- **ChromaDB:**
  - Client initialization
  - Collection creation
  - Vector storage and retrieval
  - Semantic search
  - Top-K retrieval limits
  - Malformed document filtering

- **Firebase:**
  - Connection
  - Document CRUD operations
  - Queries
  - Batch writes
  - Error handling

### 5. Modal Tests (`test_modal.py`)

Tests for Modal (secure execution environment).

```python
pytest -m modal
pytest tests/test_modal.py::TestModalCodeExecution
pytest tests/test_modal.py::TestModalDataScience
```

**Covers:**
- Simple Python execution
- Library imports (NumPy, Pandas, scikit-learn)
- 120-second timeout
- Network isolation
- File system isolation
- Memory limits
- Error handling (syntax, import, runtime)
- Security (code injection prevention)
- Output parsing (JSON, multiline, numeric)
- Data science code execution

### 6. API Tests (`test_api_endpoints.py`)

Tests for all FastAPI endpoints.

```python
pytest -m api
pytest tests/test_api_endpoints.py::TestHealthEndpoint
pytest tests/test_api_endpoints.py::TestAuthEndpoints
pytest tests/test_api_endpoints.py::TestRunsEndpoints
```

**Covers:**
- Health check
- Authentication endpoints
- Runs CRUD operations
- Paper download endpoints
- Settings endpoints
- Error handling
- Pagination and filtering
- Rate limiting
- Security headers
- Data validation

## fixtures & Utilities

### Available Fixtures (in `conftest.py`)

```python
# Database and services
mock_db                 # Mock Firestore database
mock_redis             # Mock Redis client
mock_chroma            # Mock Chroma client

# User data
mock_user              # Regular authenticated user
mock_admin_user        # Admin user

# Test data
sample_run_data        # Sample research run data
sample_llm_config      # Sample LLM configuration
sample_search_result   # Sample search results
sample_generated_code  # Sample Python code

# Utilities
capture_stdout         # Capture stdout output
temp_file             # Temporary test file
performance_timer     # Performance measurement
```

### Example Test Using Fixtures

```python
def test_with_fixtures(mock_db, sample_run_data, mock_user):
    """Example test using fixtures."""
    # mock_db is automatically provided
    mock_collection = mock_db.collection("runs")
    
    # sample_run_data contains test data
    assert sample_run_data["topic"] == "Novel AI Architecture"
    
    # mock_user is an authenticated user
    assert mock_user.id == "test_user_123"
```

## Running Tests with Coverage

### Generate Coverage Report

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View in browser
start htmlcov/index.html   # Windows
open htmlcov/index.html    # macOS
```

### Coverage Targets

- Overall: ≥ 70%
- Critical paths: ≥ 85%
- Utils: ≥ 60%

## Continuous Integration

### GitHub Actions (Recommended Setup)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio pytest-mock
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Writing New Tests

### Template: Unit Test

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestNewFeature:
    """Test new feature functionality."""
    
    def test_feature_returns_correct_value(self):
        """Verify feature returns expected value."""
        # Arrange
        expected = "result"
        
        # Act
        result = some_function()
        
        # Assert
        assert result == expected
    
    @patch("module.external_service")
    def test_feature_with_mocked_dependency(self, mock_service):
        """Test with mocked external dependency."""
        mock_service.return_value = "mocked"
        
        result = function_using_service()
        assert result == "mocked"
        mock_service.assert_called()
```

### Template: Integration Test

```python
@pytest.mark.integration
class TestIntegration:
    """Test integration with external service."""
    
    @patch("external_service.client")
    def test_integrates_with_service(self, mock_client):
        """Verify integration works correctly."""
        mock_client.connect.return_value = True
        
        result = integrated_function()
        assert result is not None
```

## Best Practices

### 1. Test Organization
- One test class per feature/component
- Descriptive test names following `test_<action>_<scenario>` pattern
- Group related tests using test classes

### 2. Mocking
- Mock external dependencies (Firebase, Redis, Chroma, etc.)
- Use fixtures for common mocks
- Verify mock calls when testing interactions

### 3. Assertions
- Use descriptive assertion messages
- Test both success and failure paths
- Validate error types and messages

### 4. Fixtures
- Use fixtures for reusable test data
- Keep fixtures focused and single-purpose
- Document fixture parameters and return values

### 5. Performance
- Mark slow tests with `@pytest.mark.slow`
- Aim for test execution < 100ms per test
- Use mocks instead of real services

### 6. Coverage
- Aim for > 70% overall coverage
- Priority: critical paths, API handlers, data persistence
- Use `pytest --cov` to identify gaps

## Troubleshooting

### Tests Fail Locally But Pass in CI

1. Check Python version consistency
2. Verify all dependencies are installed
3. Clear pytest cache: `pytest --cache-clear`
4. Check for environment variable differences

### Fixture Not Found

1. Ensure `conftest.py` is in the same directory
2. Verify fixture name is correct
3. Check fixture scope (function, class, module, session)

### Mock Not Working

1. Patch at the point of use, not import
2. Ensure mock is applied before function call
3. Use correct return value type for mock

### Timeouts in Tests

1. Increase timeout: `pytest --timeout=300`
2. Mark as slow: `@pytest.mark.slow`
3. Consider if test needs optimization

## Tips & Tricks

### Run Tests in Parallel

```bash
pip install pytest-xdist
pytest -n auto
```

### Run Tests with Detailed Output

```bash
pytest -vv --tb=long
```

### Stop on First Failure

```bash
pytest -x
```

### Repeat Failed Tests

```bash
pytest --lf  # last failed
pytest --ff  # failed first
```

### Print Debug Output

```python
def test_with_debug():
    result = some_function()
    print(f"Debug: {result}")  # Use with pytest -s
    assert result == expected
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/reference.html#fixtures)
- [Unit Testing Best Practices](https://testdriven.io/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## Maintenance

### Regular Tasks

- Review coverage reports quarterly
- Update tests when features change
- Remove tests for deprecated features
- Refactor test code for clarity

### Testing Checklist

Before committing:
- [ ] All tests pass locally
- [ ] Coverage meets requirements
- [ ] New features have tests
- [ ] Tests are maintainable
- [ ] No hardcoded values (use fixtures)

## Support

For testing issues or questions:
1. Check this guide's troubleshooting section
2. Review existing test examples
3. Consult pytest documentation
4. Ask team members in code review
