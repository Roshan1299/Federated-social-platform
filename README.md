# Federated Social Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2%2B-brightgreen.svg)](https://www.djangoproject.com/)
[<img src="https://devin.ai/assets/deepwiki-badge.png" alt="Ask DeepWiki.com" height="20"/>](https://deepwiki.com/Roshan1299/Federated-social-platform)

A distributed social networking system that enables multiple independent nodes to communicate with each other, similar to platforms like Diaspora. This project provides a decentralized alternative to centralized social media platforms.

<p align="center">
  <a href="https://www.youtube.com/watch?v=sMIH7bDkano">
    <img src="https://img.youtube.com/vi/sMIH7bDkano/hqdefault.jpg" width="700">
  </a>
</p>

## 🚀 Features

- **Federated Architecture**: Multiple independent nodes that can communicate with each other
- **User Profiles**: Complete profile management with images, GitHub integration, and bio
- **Content Creation**: Create posts with text, Markdown, or images with visibility controls
- **Social Interactions**: Follow, like, comment, and share functionality
- **Privacy Controls**: Public, unlisted, and friends-only content visibility
- **GitHub Integration**: Automatic conversion of GitHub activity to posts
- **Real-time Updates**: Push-based content distribution to followers' inboxes
- **Cross-Node Communication**: Follow and interact with users on other federated nodes

## 🏗️ Architecture

The platform follows a distributed architecture where each node operates independently while communicating with other nodes through standardized APIs. The system implements ActivityPub-like patterns for communication between nodes.

### Core Components

- **Authors**: User accounts with unique identities across the federated network
- **Posts**: Content with different visibility levels (Public, Friends-only, Unlisted)
- **Follow System**: One-way follow relationships with follow requests and approvals
- **Inbox Model**: Push-based system for content distribution to followers
- **Remote Nodes**: Configuration for connecting to other federated nodes

## 📁 Project Structure

```
├── authors/                 # Main application with models, views, etc.
├── social_distribution/     # Django project settings
├── static/                  # Static assets (CSS, JS, images)
├── media/                   # User-uploaded media files
├── docs/                    # Documentation
│   ├── api.md              # API documentation
│   └── ...
├── scripts/                 # Utility scripts
│   ├── create_superuser.py
│   ├── setup_federation.py
│   └── ...
├── deployment/             # Deployment configurations
│   ├── Procfile
│   └── runtime.txt
├── config/                 # Configuration files
├── testing_api/            # API testing utilities
├── .github/                # GitHub configuration
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── requirements.txt
├── manage.py
└── ...
```

## 🛠️ Tech Stack

- **Backend**: Django 4.2+
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: HTML, CSS, JavaScript
- **API**: RESTful API with JSON responses
- **Authentication**: Session-based for UI, HTTP Basic Auth for node-to-node
- **Deployment**: Heroku-ready with Gunicorn

## 📋 Prerequisites

- Python 3.8+
- pip package manager
- Virtual environment (recommended)

## 🚀 Getting Started

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/federated-social-platform.git
   cd federated-social-platform
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser account**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Navigate to `http://127.0.0.1:8000/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

### Environment Configuration

For production deployment, set the following environment variables:

```bash
export BASE_URL="https://your-app-name.herokuapp.com/"
export DATABASE_URL="your-database-url"
```

## 🔐 Security Features

- **API Access Control**: Visibility-based access with proper authentication
- **CSRF Protection**: All forms include CSRF tokens
- **XSS Prevention**: Input sanitization and output encoding
- **Authentication**: Session-based for UI, HTTP Basic Auth for node-to-node
- **Authorization**: Proper permission checks for all sensitive operations

## 🌐 Federation Setup

### Connecting to Other Nodes

1. **Configure your node**:
   - Login as superuser/admin
   - Visit `/node_config/` to configure your node settings
   - Enter your full URL and create service credentials

2. **Add remote nodes**:
   - Visit `/configure_remote_node/` as admin
   - Add the other party's base URL, username, and password
   - Both parties must add each other as remote nodes

3. **Follow remote authors**:
   - Navigate to the Explore page
   - Use the "Follow Remote Author" form with the author's full API URL

## 📚 API Documentation

The platform provides a comprehensive REST API for all social networking functionality. Detailed API documentation is available in the [API Documentation](./docs/api.md) file.

## 🧪 Testing

Run the project tests using:

```bash
python manage.py test authors.tests
```

This will execute all tests within the authors application.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Based on the University of Alberta CMPUT 404 project requirements
- Inspired by decentralized social networking protocols like ActivityPub
- Thanks to all team members who contributed to this project

## 🐙 GitHub Integration

The application supports automatic fetching and conversion of public GitHub activity to posts:

```bash
python manage.py fetch_github_activity
```

This command fetches public GitHub events for all authors and converts them to public posts.

---

<div align="center">
  <p>Made with ❤️ by Team Darkblue</p>
  <p>Part of the University of Alberta CMPUT 404 distributed systems course</p>
</div>
