# Architecture

This document describes the architecture of the Federated Social Platform.

## System Architecture

The Federated Social Platform follows a distributed architecture where multiple independent nodes can communicate with each other.

### Core Components

#### Authors App
The `authors` app contains all the core functionality:
- **Models**: User profiles, posts, comments, likes, and relationships
- **Views**: UI and API endpoints
- **API Views**: REST API endpoints for federation
- **Authentication**: Node-to-node and user authentication

#### Social Distribution
The main Django project that ties everything together:
- **Settings**: Configuration for the entire project
- **URLs**: Main URL routing
- **WSGI/ASGI**: Application interface

### Data Flow

1. **User Actions**: Users interact through the web interface
2. **API Processing**: Actions are processed through API endpoints
3. **Federation**: Actions are distributed to other nodes when applicable
4. **Storage**: Data is stored in the database
5. **Distribution**: Content is pushed to followers' inboxes

### Federation Model

The platform implements a push-based federation model:
- When a user creates content, it's pushed to followers' inboxes
- Remote nodes send updates via inbox endpoints
- Cross-node authentication uses HTTP Basic Auth
- Fully Qualified IDs (FQIDs) ensure unique identification across nodes

## Technology Stack

- **Backend**: Django Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: HTML/CSS/JavaScript
- **API**: RESTful endpoints with JSON
- **Authentication**: Session-based for UI, HTTP Basic for nodes
- **Deployment**: Heroku-ready with Gunicorn