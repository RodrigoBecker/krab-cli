"""Shared test fixtures for Krab CLI tests."""

import pytest

SAMPLE_SPEC_MD = """---
title: User Authentication Module
version: 2.0.0
author: Becker
---

# User Authentication Module

This module handles user authentication and authorization for the platform.

## Requirements

- The system must support OAuth2 authentication
- The system must support JWT token validation
- The system must support role-based access control
- The system must support multi-factor authentication

## Architecture

The authentication module follows hexagonal architecture patterns.
The authentication module uses clean separation of concerns.
The authentication module implements the repository pattern.

### Core Domain

The core domain contains business rules for authentication.
The core domain validates user credentials against the store.
The core domain manages session lifecycle and token refresh.

### Ports and Adapters

- Input Port: REST API endpoints for login, logout, refresh
- Input Port: GraphQL mutations for authentication
- Output Port: Database adapter for user persistence
- Output Port: Cache adapter for session management

## API Endpoints

### POST /auth/login

The login endpoint accepts user credentials and returns a JWT token.
The login endpoint validates the user credentials against the database.
The login endpoint creates a new session in the cache.

### POST /auth/logout

The logout endpoint invalidates the current session.
The logout endpoint removes the session from the cache.

### POST /auth/refresh

The refresh endpoint validates the refresh token.
The refresh endpoint issues a new access token.

## Security Considerations

The system must implement rate limiting on authentication endpoints.
The system must implement brute force protection.
The system must log all authentication attempts.
The system must encrypt sensitive data at rest.
"""

SAMPLE_SPEC_JSON = """{
  "sections": [
    {
      "heading": "API Overview",
      "level": 1,
      "content": [
        {"type": "paragraph", "text": "This API provides access to user management functions."}
      ]
    },
    {
      "heading": "Endpoints",
      "level": 2,
      "content": [
        {
          "type": "list",
          "list_type": "unordered",
          "items": [
            {"text": "GET /users — List all users", "depth": 0},
            {"text": "POST /users — Create a user", "depth": 0}
          ]
        }
      ]
    }
  ]
}"""

SAMPLE_SPEC_YAML = """sections:
  - heading: Database Schema
    level: 1
    content:
      - type: paragraph
        text: The database uses PostgreSQL with the following tables.
  - heading: Users Table
    level: 2
    content:
      - type: list
        list_type: unordered
        items:
          - text: "id: UUID primary key"
            depth: 0
          - text: "email: VARCHAR(255) unique"
            depth: 0
          - text: "created_at: TIMESTAMP"
            depth: 0
"""


@pytest.fixture
def sample_md():
    return SAMPLE_SPEC_MD


@pytest.fixture
def sample_json():
    return SAMPLE_SPEC_JSON


@pytest.fixture
def sample_yaml():
    return SAMPLE_SPEC_YAML


@pytest.fixture
def tmp_spec_file(tmp_path, sample_md):
    """Create a temporary spec markdown file."""
    spec_file = tmp_path / "test_spec.md"
    spec_file.write_text(sample_md, encoding="utf-8")
    return spec_file


@pytest.fixture
def tmp_json_file(tmp_path, sample_json):
    """Create a temporary JSON spec file."""
    f = tmp_path / "test_spec.json"
    f.write_text(sample_json, encoding="utf-8")
    return f


@pytest.fixture
def tmp_yaml_file(tmp_path, sample_yaml):
    """Create a temporary YAML spec file."""
    f = tmp_path / "test_spec.yaml"
    f.write_text(sample_yaml, encoding="utf-8")
    return f
