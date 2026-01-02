# Contributing Guide

Thank you for your interest in contributing to the AI Agent Framework!

## Development Setup

### Prerequisites

- Python 3.9+
- pip
- git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/agent-framework.git
cd agent-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Environment Variables

Create a `.env` file for development:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini
JOB_ID=dev-local
```

## Project Structure

```
agent-framework/
├── src/agent_framework/    # Main package
│   ├── core/               # Core classes (Agent, ManagerAgent)
│   ├── components/         # Memory, tools, subscribers
│   ├── policies/           # Behavior policies
│   ├── planners/           # Planning engines
│   ├── gateways/           # LLM providers
│   └── templates/          # Sample applications
├── tests/                  # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                   # Documentation
└── examples/               # Example projects
```

## Code Style

### Python Style

We follow PEP 8 with these additions:

- Maximum line length: 100 characters
- Use type hints for all public functions
- Use docstrings for all public classes and methods

### Example

```python
from typing import Optional, List, Dict, Any


class MyComponent:
    """A component that does something useful.

    Args:
        name: The component name
        config: Optional configuration dictionary
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    async def process(self, data: List[str]) -> Dict[str, Any]:
        """Process the input data.

        Args:
            data: List of strings to process

        Returns:
            Dictionary with processing results
        """
        # Implementation
        return {"processed": len(data)}
```

### Formatting

We use `black` and `isort`:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check formatting
black --check src/ tests/
isort --check src/ tests/
```

### Linting

We use `flake8` and `mypy`:

```bash
# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=agent_framework

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/  # Requires OPENAI_API_KEY
```

### Writing Tests

1. Place tests in the appropriate directory
2. Name test files `test_*.py`
3. Name test functions `test_*`
4. Use `@pytest.mark.asyncio` for async tests
5. Mock external dependencies in unit tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_my_feature():
    # Arrange
    component = MyComponent("test")

    # Act
    result = await component.process(["a", "b", "c"])

    # Assert
    assert result["processed"] == 3
```

## Documentation

### Building Docs

```bash
cd docs
sphinx-build -b html . _build/html
```

### Writing Docs

- Use Markdown for guides (`.md`)
- Use reStructuredText for API docs (`.rst`)
- Include code examples
- Update the table of contents in `index.rst`

## Pull Request Process

1. **Create a branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run checks**
   ```bash
   # Format
   black src/ tests/
   isort src/ tests/

   # Lint
   flake8 src/ tests/
   mypy src/

   # Test
   pytest
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

### Commit Messages

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance

## Adding New Components

### New Tool

1. Create tool class in `src/agent_framework/components/tools/`
2. Register in the tool registry
3. Add unit tests
4. Document in `docs/guides/tools.md`

### New Policy

1. Create policy class in `src/agent_framework/policies/`
2. Register in the policy registry
3. Add to presets if common
4. Add unit tests
5. Document in `docs/guides/policy-presets.md`

### New Gateway

1. Create gateway class in `src/agent_framework/gateways/`
2. Register in the gateway registry
3. Add unit and integration tests
4. Document in `docs/guides/planners.md`

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues before creating new ones
