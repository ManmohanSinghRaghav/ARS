# ARS Backend Test Quick Reference

## Installation

```bash
cd backend
pip install -r requirements-test.txt
```

## Run All Tests

```bash
pytest
pytest -v              # Verbose
pytest -vv             # Very verbose
pytest --tb=short      # Short traceback
```

## Run by Category

```bash
# Fast unit tests
pytest -m unit

# Integration tests  
pytest -m integration

# Specific feature tests
pytest -m agents       # Agent tests
pytest -m tools        # Tool tests
pytest -m pipeline     # Pipeline tests
pytest -m modal        # Modal tests
pytest -m api          # API tests
pytest -m redis        # Redis tests
pytest -m chromadb     # ChromaDB tests
pytest -m firebase     # Firebase tests
```

## Run Specific Tests

```bash
# Single file
pytest tests/test_agents.py

# Single class
pytest tests/test_agents.py::TestAgentCreation

# Single test
pytest tests/test_agents.py::TestAgentCreation::test_researcher_agent_creation

# Multiple tests
pytest tests/test_agents.py tests/test_tools.py
```

## Coverage

```bash
# Generate coverage report
pytest --cov=app tests/

# HTML report
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html

# With minimum threshold
pytest --cov=app --cov-fail-under=70 tests/
```

## Useful Flags

```bash
pytest -x             # Stop on first failure
pytest --lf           # Run last failed
pytest --ff           # Run failed first
pytest -k "search"    # Run tests matching pattern
pytest -m "not slow"  # Skip slow tests
pytest -s             # Show print statements
pytest --durations=10 # Show 10 slowest tests
pytest -n auto        # Parallel (requires pytest-xdist)
```

## Test Files Overview

| File | Purpose | Tests |
|------|---------|-------|
| `test_agents.py` | Agent orchestration | 15+ |
| `test_tools.py` | Search & execution tools | 20+ |
| `test_pipeline_runner.py` | Pipeline execution | 15+ |
| `test_integrations.py` | Redis, ChromaDB, Firebase | 35+ |
| `test_modal.py` | Modal code execution | 20+ |
| `test_api_endpoints.py` | API endpoints | 50+ |
| `test_e2e_integration.py` | End-to-end workflows | 15+ |

**Total: 170+ tests**

## Test Structure

- ✅ All tests are independent and can run in any order
- ✅ Fixtures provide common setup (mocks, test data)
- ✅ Markers organize tests by category
- ✅ Coverage tracking for code quality
- ✅ Error handling extensively tested

## CI/CD Integration

Tests automatically run on:
- Push to main/develop branches
- Pull requests
- Scheduled nightly runs

## Common Tasks

### Add New Test

1. Create test file: `test_module.py`
2. Add test class: `class TestNewFeature:`
3. Write test method: `def test_something():`
4. Use fixtures from `conftest.py`
5. Run: `pytest tests/test_module.py -v`

### Update Existing Tests

```bash
# Find what changed
git diff

# Run related tests
pytest tests/test_modified_module.py -v

# Check coverage of changes
pytest --cov=app tests/test_modified_module.py --cov-report=term-missing
```

### Debug Failed Test

```bash
# Run with verbose output
pytest tests/test_file.py::TestClass::test_method -vv

# Run with print statements
pytest tests/test_file.py::TestClass::test_method -s

# Run with debugging
pytest --pdb tests/test_file.py::TestClass::test_method
```

## Key Test Coverage

### Agents (test_agents.py)
- ✅ Agent creation & initialization
- ✅ Agent delegation & handoffs
- ✅ Output validation
- ✅ Error handling
- ✅ Progress tracking

### Tools (test_tools.py)
- ✅ ArXiv search (top-3)
- ✅ Web search (top-3)
- ✅ Sandbox execution
- ✅ Timeout handling
- ✅ Error recovery
- ✅ Security

### Pipeline (test_pipeline_runner.py)
- ✅ Run creation
- ✅ Background execution
- ✅ Firestore persistence
- ✅ Error handling
- ✅ Input validation

### Integrations (test_integrations.py)
- ✅ Redis caching
- ✅ ChromaDB vectors
- ✅ Firebase CRUD
- ✅ Error fallbacks
- ✅ Performance

### Modal (test_modal.py)
- ✅ Code execution
- ✅ Timeout enforcement
- ✅ Security isolation
- ✅ Error handling
- ✅ Library imports
- ✅ Output parsing

### API (test_api_endpoints.py)
- ✅ Health checks
- ✅ Authentication
- ✅ CRUD operations
- ✅ Error responses
- ✅ Pagination
- ✅ Validation

## Tips

1. **Mock external services** - Use `@patch` to mock Firebase, Redis, Chroma
2. **Use fixtures** - Reuse common setup from `conftest.py`
3. **Test both success and failure** - Cover happy path and error cases
4. **Keep tests focused** - One assertion per concept when possible
5. **Run locally first** - Before pushing, verify tests pass locally

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ImportError | Ensure `__init__.py` exists in directories |
| Fixture not found | Check fixture defined in `conftest.py` |
| Mock not working | Patch at point of use, e.g., `@patch('app.module.function')` |
| Tests hang | Use `pytest --timeout=10` or check infinite loops |
| Inconsistent results | Check for test interdependencies or setup issues |

## Resources

- Tests Guide: `tests/TESTING_GUIDE.md`
- Pytest Docs: https://docs.pytest.org/
- Mock Docs: https://docs.python.org/3/library/unittest.mock.html
