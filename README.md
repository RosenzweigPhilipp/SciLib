# SciLib

An AI-powered scientific literature manager for researchers, students, and academics.

## Features

- 📚 **Library Management**: Upload, organize, and manage scientific papers
- 🔍 **Smart Search**: Full-text and metadata-based search capabilities
- 🏷️ **Tagging System**: Custom tags and collections for organization
- 🤖 **AI Insights**: Automated summaries and paper analysis (Phase 2)
- 💬 **RAG Chat**: Ask questions about your research library (Phase 2)
- 🔗 **Discovery**: Find related papers and recommendations (Phase 2)

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JavaScript
- **AI**: LangChain + LangSmith (Phase 2)

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd SciLib
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
python -m app.database.init_db
```

6. Run the application:
```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

## Project Structure

```
SciLib/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── auth.py                # API key authentication
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py      # Database connection
│   │   ├── models.py          # SQLAlchemy models
│   │   └── init_db.py         # Database initialization
│   ├── api/
│   │   ├── __init__.py
│   │   ├── papers.py          # Papers endpoints
│   │   ├── collections.py     # Collections endpoints
│   │   └── tags.py            # Tags endpoints
│   └── services/
│       ├── __init__.py
│       └── paper_service.py   # Business logic
├── static/
│   ├── css/
│   ├── js/
│   └── index.html
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
isort app/
```

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "Add your feature"`
3. Push to branch: `git push origin feature/your-feature`
4. Submit a pull request

## License

MIT License - see LICENSE file for details.