# SciLib 📚

An AI-powered scientific literature manager designed for researchers, students, and academics. SciLib combines the organizational capabilities of reference managers like Mendeley or Zotero with modern AI tooling to accelerate literature discovery, comprehension, and cross-paper insight.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

### 📚 Library Management
- **PDF Upload**: Drag-and-drop interface for easy paper uploads
- **Smart Organization**: Collections and folders for structured organization  
- **Custom Tagging**: Color-coded tags for flexible categorization
- **Full-Text Search**: Search across titles, authors, and abstracts

### 🎯 Current Capabilities (Phase 1)
- ✅ Upload and store PDF papers with validation
- ✅ Create and manage collections for organization
- ✅ Tag papers with custom colored labels
- ✅ Search and filter papers by metadata
- ✅ Responsive web interface for all devices
- ✅ RESTful API with automatic documentation

### 🚀 Coming Soon (Phase 2)
- 🤖 **AI Insights**: Automated summaries and paper analysis
- 💬 **RAG Chat**: Ask questions about your research library  
- 🔗 **Discovery**: Find related papers and recommendations
- 📊 **Analytics**: Research trends and citation analysis

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python) with async support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: Modern HTML5/CSS3/JavaScript (no frameworks)
- **Authentication**: API key-based security
- **File Storage**: Local filesystem with configurable paths
- **Future**: LangChain + LangSmith for AI features

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12+ (or SQLite for testing)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/SciLib.git
cd SciLib
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your database settings
```

4. **Initialize database** (PostgreSQL)
```bash
# Create PostgreSQL database first
createdb scilib_db
python -m app.database.init_db
```

5. **Start the application**
```bash
uvicorn app.main:app --reload
```

6. **Open in browser**
   - Frontend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Quick Test (SQLite)

For testing without PostgreSQL:
```bash
python app/main_test.py
```

## 📁 Project Structure

```
SciLib/
├── app/                        # Backend application
│   ├── api/                   # REST API endpoints
│   │   ├── papers.py          # Paper management
│   │   ├── collections.py     # Collection management
│   │   └── tags.py           # Tag management
│   ├── database/              # Database layer
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── connection.py      # DB connection
│   │   └── init_db.py         # DB initialization
│   ├── main.py                # FastAPI app
│   ├── config.py              # Settings
│   └── auth.py                # Authentication
├── static/                    # Frontend assets
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript modules
│   └── index.html             # Main interface
├── uploads/                   # File storage
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── docs/                     # Documentation
```

## 🔌 API Usage

All endpoints require API key authentication:

```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/api/papers
```

### Key Endpoints

- `POST /api/papers/upload` - Upload PDF paper
- `GET /api/papers` - List papers with search/pagination
- `POST /api/collections` - Create collection
- `POST /api/tags` - Create tag
- `GET /docs` - Interactive API documentation

## 🎨 Screenshots

### Dashboard
Modern, clean interface showing library statistics and recent papers.

### Paper Upload
Intuitive drag-and-drop interface with progress indication.

### Library Management
Organized view with search, filtering, and batch operations.

## 🔄 Development Workflow

This project follows a structured development approach:

### Branching Strategy
- `main` - Production-ready code
- `feature/backend-setup` - Backend infrastructure  
- `feature/database-setup` - Database implementation
- `feature/frontend-init` - Frontend development
- `feature/ai-integration` - AI features (Phase 2)

### Commit Conventions
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation updates
- `style:` - Code formatting
- `refactor:` - Code restructuring

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'feat: add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Code formatting
black app/ && isort app/

# Type checking
mypy app/
```

## 📊 Current Status

**Phase 1: ✅ Complete**
- Backend API with FastAPI
- Database models and CRUD operations
- Frontend interface with modern design
- File upload and management
- Search and organization features

**Phase 2: 🚧 Planned**
- AI-powered document analysis
- Semantic search with embeddings
- Chat interface for Q&A
- Automated insights and summaries

## 📄 Documentation

- [Setup Guide](SETUP.md) - Detailed installation instructions
- [Project Outline](PROJECT_OUTLINE.md) - Architecture and planning
- [Development Summary](DEVELOPMENT_SUMMARY.md) - Progress tracking
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

## 🐛 Troubleshooting

**Database Issues**
```bash
# Check PostgreSQL status
pg_isready

# Reset database
dropdb scilib_db && createdb scilib_db
python -m app.database.init_db
```

**Port Conflicts**
```bash
# Use different port
uvicorn app.main:app --port 8001
```

## 🔮 Future Roadmap

### Phase 2: AI Integration (Q1 2024)
- [ ] Document text extraction and parsing
- [ ] LangChain integration for summarization
- [ ] Vector database for semantic search
- [ ] Chat interface for document Q&A

### Phase 3: Advanced Features (Q2 2024)
- [ ] Related paper recommendations
- [ ] Author profiling and networks
- [ ] Citation analysis and trends
- [ ] Export capabilities (BibTeX, etc.)

### Phase 4: Collaboration (Q3 2024)
- [ ] Multi-user support
- [ ] Shared libraries and annotations
- [ ] Real-time collaboration features
- [ ] Mobile application

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/your-username/SciLib/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/SciLib/discussions)
- **Email**: your-email@example.com

---

**Built with ❤️ for the research community**

*SciLib - Accelerating literature discovery, comprehension, and insight*