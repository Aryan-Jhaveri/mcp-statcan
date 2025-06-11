# Contributing to Statistics Canada MCP Server

Thank you for your interest in contributing to the Statistics Canada MCP Server! This project provides tools for interacting with Statistics Canada data APIs through the Model Context Protocol (MCP), enabling LLMs and other clients to access Canadian statistical data.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Architecture](#project-architecture)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Types of Contributions](#types-of-contributions)
- [Future Development](#future-development)

## Getting Started

### Prerequisites

- **Python 3.10+** - Download from [python.org](https://www.python.org/downloads/)
- **UV** - Fast Python package installer
- **Git** - For version control
- Basic familiarity with:
  - Python async/await patterns
  - REST APIs
  - Model Context Protocol (MCP) concepts
  - Statistics Canada data structure (helpful but not required)

### Quick Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp-statcan.git
   cd mcp-statcan
   ```

2. **Install UV** (if not already installed):
   ```bash
   curl -fsSL https://astral.sh/uv/install.sh | bash
   ```

3. **Install dependencies**:
   ```bash
   uv pip install fastmcp httpx pydantic
   # Development dependencies
   uv pip install pytest black isort
   ```

## Development Environment Setup

### Environment Variables


```bash
# Database configuration
STATCAN_DB_FILE=temp_statcan_data.db

# Debug flags
STATCAN_SERVER_DEBUG=true
STATCAN_SSL_WARNINGS=false
STATCAN_SQL_DEBUG=false
STATCAN_DATA_VALIDATION_WARNINGS=true
STATCAN_SEARCH_PROGRESS=true
```

## Project Architecture

### Directory Structure

```
mcp-statcan/
├── src/
│   ├── __init__.py
│   ├── server.py              # Main FastMCP server entry point
│   ├── config.py              # Configuration management
│   ├── api/                   # MCP tools for StatCan API
│   │   ├── cube_tools.py      # Data cube operations
│   │   ├── vector_tools.py    # Vector data operations
│   │   └── metadata_tools.py  # Metadata and code sets
│   ├── db/                    # Database operations
│   │   ├── connection.py      # SQLite connection management
│   │   ├── queries.py         # Database tools registration
│   │   └── schema.py          # Table schema operations
│   ├── models/                # Pydantic data models
│   │   ├── api_models.py      # API request/response models
│   │   └── db_models.py       # Database models
│   └── util/                  # Utility functions
│       ├── coordinate.py      # Coordinate padding utilities
│       └── sql_helpers.py     # SQL query helpers
├── pyproject.toml            # Project configuration
└── README.md                 # Project overview
```

### Key Components

1. **FastMCP Server** (`server.py`): Main entry point that registers all MCP tools
2. **API Tools**: Wrappers around Statistics Canada Web Data Service API
3. **Database Layer**: SQLite integration for data persistence and querying
4. **Models**: Pydantic models for data validation and serialization
5. **Configuration**: Environment-based configuration management

## Development Workflow

### Branch Naming Convention

Use descriptive branch names with prefixes:

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements

Examples:
- `feature/add-windows-installation-guide`
- `fix/ssl-verification-error`
- `docs/update-api-examples`

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code standards below

   ```bash
   git add .
   git commit -m "Add descriptive commit message"
   ```

3. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Standards

### Python Style Guidelines

- **Type hints** - Use type hints for all function parameters and return values
- **Async/await** - Use async functions for API calls and database operations
- **Error handling** - Use try/except blocks with specific exception types
- **Logging** - Use the project's logging configuration for debug output

### Code Organization

- **Imports**: Use `isort` for consistent import ordering
- **Functions**: Keep functions focused and single-purpose
- **Classes**: Use Pydantic models for data validation
- **Constants**: Define constants in `config.py`

### Example Code Style

```python
from typing import List, Optional
from pydantic import BaseModel
import httpx

class VectorDataInput(BaseModel):
    """Input model for vector data requests."""
    vector_id: int
    latest_n: int
    
async def get_vector_data(
    input_data: VectorDataInput
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve vector data from Statistics Canada API.
    
    Args:
        input_data: Vector data request parameters
        
    Returns:
        List of data points or None if request fails
        
    Raises:
        httpx.HTTPError: If API request fails
    """
    try:
        # Implementation here
        pass
    except httpx.HTTPError as e:
        log_server_debug(f"API request failed: {e}")
        raise
```

### Security Considerations

- **Never commit sensitive data** - Use environment variables
- **SSL verification** - Enable SSL verification in production
- **Input validation** - Always validate user inputs with Pydantic models
- **SQL injection prevention** - Use parameterized queries

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_api_tools.py

# Run with debug output
pytest -v -s
```

### Test Structure

Tests should be organized to mirror the source structure:

```
tests/
├── test_api/
│   ├── test_cube_tools.py
│   ├── test_vector_tools.py
│   └── test_metadata_tools.py
├── test_db/
│   └── test_queries.py
└── test_models/
    └── test_api_models.py
```

### Writing Tests

- **Unit tests** - Test individual functions and classes
- **Integration tests** - Test API interactions (with mocking)
- **Database tests** - Test database operations with temporary databases
- **Use fixtures** - Create reusable test data with pytest fixtures

Example test:

```python
import pytest
from src.models.api_models import VectorLatestNInput

def test_vector_latest_n_input_validation():
    """Test VectorLatestNInput model validation."""
    # Valid input
    valid_input = VectorLatestNInput(vectorId=12345, latestN=5)
    assert valid_input.vectorId == 12345
    assert valid_input.latestN == 5
    
    # Invalid input
    with pytest.raises(ValueError):
        VectorLatestNInput(vectorId="invalid", latestN=5)
```

## Documentation

### Code Documentation

- **Docstrings** - Use Google-style docstrings for all public functions and classes
- **Type hints** - Include comprehensive type annotations
- **Comments** - Add comments for complex logic, not obvious code
- **API documentation** - Update tool descriptions when adding new MCP tools

### Documentation Updates

When making changes, update relevant documentation:

- **README.md** - For new features or installation changes
- **API examples** - Add examples in `docs/examples/`
- **Code comments** - Update docstrings and inline comments
- **Configuration docs** - Update environment variable documentation

### Example Documentation

```python
async def search_cubes_by_title(title: str) -> List[CubeMetadata]:
    """
    Search for data cubes by title keyword.
    
    This function searches Statistics Canada's data cubes using a title
    keyword and returns matching cube metadata.
    
    Args:
        title: Search keyword for cube titles
        
    Returns:
        List of CubeMetadata objects containing cube information
        
    Raises:
        httpx.HTTPError: If the API request fails
        ValueError: If the title parameter is empty
        
    Example:
        >>> cubes = await search_cubes_by_title("employment")
        >>> print(f"Found {len(cubes)} cubes")
    """
```

## Pull Request Process

### Before Submitting

1. **Run all checks**:
   ```bash
   black src/
   isort src/
   pytest
   ```

2. **Update documentation** if needed

3. **Test your changes** thoroughly

4. **Update IMPLEMENTATIONS.md** if implementing planned features

### Pull Request Template

When creating a pull request, include:

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (please describe)

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No sensitive data included
```

### Review Process

1. **Automated checks** - CI/CD pipeline runs tests and formatting checks
2. **Code review** - Project maintainers review code quality and design
3. **Testing** - Ensure changes don't break existing functionality
4. **Documentation** - Verify documentation is updated and accurate

## Types of Contributions

### 🐛 Bug Fixes

- SSL verification issues
- API endpoint errors
- Database connection problems
- Data validation failures

### ✨ New Features

Priority areas from `IMPLEMENTATIONS.md`:

- Windows installation guides
- Package installer improvements
- Enhanced tool prompts for LLM efficiency
- Additional database math tools
- Graph visualization tools
- Scheduled report generation

### 📚 Documentation

- API usage examples
- Installation guides for different platforms
- Integration documentation
- Code examples and tutorials

### 🧪 Testing

- Unit test coverage improvements
- Integration test development
- Performance testing
- API mocking improvements

### 🛠️ Infrastructure

- CI/CD pipeline improvements
- Development environment enhancements
- Performance optimizations
- Security improvements

## Future Development

### Current Roadmap

Based on `IMPLEMENTATIONS.md`, priority areas include:

1. **Package Management**: UV/Smithery installer for direct LLM client installation
2. **Platform Support**: Windows installation guides and setup scripts
3. **LLM Optimization**: Improved tool prompts to reduce unnecessary API calls
4. **Database Enhancements**: Math tools and visualization capabilities
5. **Automation**: Scheduled reporting and data update systems

### Architecture Considerations

- **Multi-agent systems**: Potential A2A + MCP integration
- **Performance**: Bulk operation optimization
- **Scalability**: Database connection pooling
- **Security**: SSL verification and input validation improvements

### Getting Involved

To contribute to future development:

1. **Check IMPLEMENTATIONS.md** for current priorities
2. **Join discussions** on GitHub issues
3. **Propose new features** through issue templates
4. **Review architecture** diagrams and provide feedback

## Questions or Need Help?

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and brainstorming
- **Documentation**: Check the `docs/` directory for detailed guides
- **Code Examples**: See `docs/examples/` for usage patterns

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

---
