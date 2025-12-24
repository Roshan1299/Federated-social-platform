# Contributing to Federated Social Platform

Thank you for your interest in contributing to the Federated Social Platform! We welcome contributions from the community and are excited to work with you.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Development Setup](#development-setup)
4. [Pull Request Process](#pull-request-process)
5. [Style Guides](#style-guides)
6. [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

- Use a clear and descriptive title for the issue
- Describe the exact steps which reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed after following the steps
- Explain which behavior you expected to see instead
- Include screenshots and animated GIFs if possible

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

- Use a clear and descriptive title
- Provide a step-by-step description of the suggested enhancement
- Provide specific examples to demonstrate the steps
- Describe the current behavior and explain the behavior you expected to see instead
- Explain why this enhancement would be useful

### Pull Requests

- Fill in the provided PR template
- Do not include issue numbers in the PR title
- Include screenshots and animated GIFs in your pull request when possible
- Follow the Python styleguides
- End all files with a newline

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/federated-social-platform.git
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Set up the database:
   ```bash
   python manage.py migrate
   ```
6. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build
2. Update the README.md with details of changes to the interface
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you

## Style Guides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Python Style Guide

- Follow PEP 8 guidelines
- Use 4 spaces for indentation
- Use descriptive variable and function names
- Write docstrings for all public methods and classes
- Keep functions and methods focused on a single responsibility

### Django Best Practices

- Follow Django's coding style
- Use Django's built-in form validation
- Implement proper authentication and authorization
- Use Django's ORM properly to avoid N+1 queries
- Follow security best practices

## Community

- Check the project's GitHub issues for anything tagged with `help wanted`
- Look for anything tagged with `first-timers-only` if you're new to the project
- Join our community discussions (if applicable)
- Follow our social media channels (if applicable)

---

Thank you for your contributions! Together, we can build a better federated social platform.