# Contributing to DroidRun

Thank you for your interest in contributing to DroidRun! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/droidrun.git
   cd droidrun
   ```
3. Set up your development environment as described below

## Development Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Making Contributions

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards:
   - Use type hints for Python functions
   - Follow PEP 8 style guidelines
   - Write descriptive commit messages
   - Update documentation as needed

3. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Open a Pull Request

## Documentation

- Update the README.md if you change functionality
- Add docstrings to new functions and classes
- Update the documentation in the `docs/` directory

## Community

- Join our [Discord server](https://discord.gg/ZZbKEZZkwK) for discussions
- Follow us on [Twitter/X](https://x.com/droid_run)
- Check our [Documentation](https://docs.droidrun.ai)
- Report bugs and request features through [GitHub Issues](https://github.com/droidrun/droidrun/issues)

## Pull Request Process

1. Update documentation for any modified functionality
2. Update the changelog if applicable
3. Get at least one code review from a maintainer
4. Once approved, a maintainer will merge your PR

## Release Process

Releases are handled by the maintainers. Version numbers follow [Semantic Versioning](https://semver.org/).

## Questions?

If you have questions about contributing:
1. Check existing GitHub issues
2. Ask in our Discord server
3. Open a new GitHub issue for complex questions

Thank you for contributing to DroidRun! 🚀

## Language

English is the preferred language for all contributions, including:
- Code comments
- Documentation
- Commit messages
- Pull requests
- Issue reports
- Community discussions