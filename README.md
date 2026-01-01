# SciLib - AI-Powered Scientific Literature Manager

A modern web application for managing and organizing scientific literature with AI integration capabilities.

## 🚀 Features

### Core Features
- **Paper Management**: Upload, view, edit, and delete PDF papers with AI metadata extraction
- **Smart Collections**: AI-powered automatic paper classification into research fields
- **Manual Collections & Tags**: Organize papers into custom collections and tag them
- **Advanced Search**: Semantic search using vector embeddings + traditional keyword search
- **Similar Papers**: Find related papers in your library and discover external papers
- **Citation Analysis**: Track citation networks and calculate influence metrics
- **Secure Authentication**: Session-based authentication system (no hardcoded API keys)
- **Background Processing**: Celery-powered asynchronous tasks for metadata extraction
- **Responsive UI**: Modern, clean interface with badge-style collections
pgvector extension for vector search
- **Task Queue**: Celery + Redis for background processing
- **AI/ML**: OpenAI GPT-4o-mini for classification, text-embedding-3-small for vectors
- **Scientific APIs**: CrossRef, arXiv, Semantic Scholar, OpenAlex
- **Frontend**: Vanilla JavaScript with modular architecture
- **Authentication**: Session-based with X-API-Key header
- **PDF Processing**: PyMuPDF, pdfplumber, Tesseract OCR
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Authentication**: JWT-like session tokens
- **File Upload**: PDF processing and storage

## ⚡ Quick Start

### Prerequi with pgvector extension
- Redis server
- Git
- Tesseract OCR (optional, for scanned PDFs)
- Python 3.8+
- PostgreSQL
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/RosenzweigPhilipp/SciLib.git
   cd SciLib
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and API key
   ```

5. **Enable pgvector extension
   psql scilib_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   
   # The app will auto-create tables on first run
   ```

6. **Start Redis**
   ```bash
   redis-server
   ```

7. **Run the application**
   
   **Option A: Use the convenience script (recommended)**
   ```bash
   ./start_scilib.sh          # Production mode
   ./start_scilib.sh --dev    # Development mode with auto-reload
   ```
   
   **Option B: Manual startup (3 terminals)**
   ```bash
   # Terminal 1: Redis
   redis-server
   
   # Termi/                    # AI integration
│   │   ├── agents/           # Metadata extraction pipeline
│   │   ├── extractors/       # PDF text extraction
│   │   ├── services/         # Smart collection service
│   │   ├── tools/            # Scientific API integrations
│   │   ├── endpoints.py      # AI endpoints
│   │   └── tasks.py          # Celery background tasks
│   ├── api/                   # REST API endpoints
│   │   ├── papers.py         # Paper CRUD
│   │   ├── collections.py    # Collection management
│   │   ├── tags.py           # Tag management
│   │   └── smart_collections.py  # AI collection endpoints
│   ├── database/              # Database layer
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── connection.py     # DB connection
│   │   └── init_db.py        # Initialization
│   ├── auth.py               # Authentication
│   ├── config.py             # Configuration
│   ├── main.py               # FastAPI app
│   └── celery_worker.py      # Celery worker entry point
├── static/
│   ├── css/
│   │   ├── main.css          # Main styles
│   │   └── components.css    # Component styles
│   ├── js/
│   │   ├── main.js           # Application logic
│   │   ├── components.js     # UI components
│   │   └── api.js            # API client

# OpenAI (REQUIRED for AI features)
OPENAI_API_KEY=sk-...

# Celery & Redis
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379

# Optional API Keys (for enhanced features)
EXA_API_KEY=...                      # Enhanced web search
CROSSREF_EMAIL=your@email.com        # Higher CrossRef rate limits

# Server
HOST=127.0.0.1
PORT=8000
DEBUG=Falser your API key from the .env file to login

## 🔐 Security

- **No hardcoded secrets**: All sensitive data is stored in environment variables
- **Session-based auth**: API keys are exchanged for temporary session tokens
- **Token expiration**: Sessions automatically expire after 24 hours
- **Secure uploads**: File validation and secure storage

## 📁 Project Structure

```
SciLib/
├── app/
│   ├── api/              # API route handlers
│   ├── database/         # Database models and setup
│   ├── auth.py          # Authentication logic
│   ├── config.py        # Configuration management
│   └── main.py          # FastAPI application
├── static/
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript modules
│   └── index.html       # Main frontend
├── uploads/             # PDF file storage (gitignored)
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
└── README.md           # This file
```

## 🔑 Configuration

Edit `.env` file with your settings:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost/scilib_db

# Security
API_KEY=your-secret-api-key-here
DEBUG=True

# OpenAI (optional, for future AI features)
OPENAI_API_KEY=your-openai-api-key-here

# Server
HOST=127.0.0.1
PORT=8000

# Upload settings
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50000000
```# Branch 7: Smart Collections ✅
- ✅ AI-powered paper classification into research fields
- ✅ GPT-4o-mini classification with confidence scoring
- ✅ Automatic classification on paper upload
- ✅ Manual re-classification and bulk operations
- ✅ Badge-style UI with purple gradient for smart collections
- ✅ Toggle smart collections on/off via settings

### Phase 3: Literature Intelligence 📋 PLANNED

#### Branch 8: Literature Review Generator 📋 FUTURE
- 📋 Automated literature review generation
- 📋 Citation-aware summaries
- 📋 Research gap identification
- 📋Phase 1: Core Infrastructure ✅ COMPLETE
- ✅ Backend API with FastAPI
- ✅ PostgreSQL database with SQLAlchemy ORM
- ✅ File upload and PDF storage system
- ✅ Frontend interface with CRUD operations directly (free, no LLM)
- **Multi-API Search**: CrossRef, arXiv, Semantic Scholar, OpenAlex with fallback chain
- **LLM Validation**: Optional GPT-4o-mini for conflict resolution (disabled by default)
- **Confidence Scoring**: 0.0-1.0 confidence with detailed source tracking
- **Background Processing**: Celery tasks for non-blocking extraction
- **OCR Fallback**: Tesseract OCR for scanned PDFs

### Smart Collections
- **AI Classification**: GPT-4o-mini automatically classifies papers into 1-3 research fields
- **Field Descriptions**: Each collection includes a detailed field description
- **Automatic Workflow**: Classification triggers after successful metadata extraction
- **Manual Control**: Re-classify individual papers or entire library
- **Badge UI**: Visual distinction with purple gradient for smart collections vs blue for manual
- **Toggle Feature**: Enable/disable smart collections via settings

### Semantic Search & Discovery
- **Embedding Generation**: OpenAI text-embedding-3-small (1536 dimensions)
- **Vector Search**: pgvector with cosine similarity for semantic matching
- **Hybrid Ranking**: Combines semantic similarity with keyword relevance
- **External Discovery**: Search 4 scientific databases simultaneously
- **Similar Papers**: Find related papers in your library with confidence scores

### Citation Intelligence
- **Bidirectional Tracking**: Papers cited and citing relationships
- **Influence Metrics**: 4-factor composite score (citations, velocity, h-index, centrality)
- **Network Analysis**: Cluster detection using connected components
- **External Integration**: Semantic Scholar API for citation counts
- **Auto-Updates**: PostgreSQL triggers for real-time count maintenance
- **Query Interface**: Find most influential/cited papers
#### Branch 3: Vector Search ✅
- ✅ Semantic search using OpenAI embeddings
- ✅ Hybrid search (semantic + keyword)
- ✅ Automatic embedding generation
- ✅ Cosine similarity ranking

#### Branch 4: Internal Recommendations ✅
- ✅ Similar paper recommendations
- ✅ Hybrid ranking (embedding + metadata)
- ✅ Recommendation scoring system
- ✅ Collection-based filtering

#### Branch 5: External Paper Discovery ✅
- ✅ Multi-source search (Semantic Scholar, arXiv, CrossRef, OpenAlex)
- ✅ DOI-based deduplication
- ✅ Relevance ranking (position + citations)
- ✅ Direct import to library
- ✅ Library status detection

#### Branch 6: Citation Analysis ✅
- ✅ Citation network tracking
- ✅ Influence score calculation (4-factor formula)
- ✅ H-index and centrality metrics
- ✅ External citation data (Semantic Scholar API)
- ✅ Citation network visualization support
- ✅ Cluster detection (connected components)
- ✅ Most influential/cited papers queries

### Phase 3: Literature Intelligence 🔄 IN PROGRESS

#### Branch 7: Literature Review Generator 🔄 NEXT
- 🔄 Automated literature review generation
- 🔄 Citation-aware summaries
- 🔄 Research gap identification
- 🔄 Markdown/PDF export

### Phase 4: Frontend Enhancement 📋 PLANNED
- 📋 Citation network visualization (D3.js/Cytoscape.js)
- 📋 Interactive influence rankings
- 📋 Advanced search UI with filters
- 📋 Literature review editor
- 📋 Export templates and formatting

## 🎯 Key Features Implemented

### AI-Powered Metadata Extraction
- **DOI-First Strategy**: Extract DOI from PDF → query scientific APIs
- **Multi-API Search**: CrossRef, arXiv, Semantic Scholar, OpenAlex
- **LLM Validation**: Optional GPT-4o-mini for conflict resolution
- **Confidence Scoring**: 0.0-1.0 confidence with source tracking

### Semantic Search & Discovery
- **Embedding Generation**: OpenAI text-embedding-3-small
- **Vector Search**: pgvector with cosine similarity
- **Hybrid Ranking**: Combines semantic and keyword relevance
- **External Discovery**: Search 4 scientific databases simultaneously

### Citation Intelligence
- **Bidirectional Tracking**: Papers cited and citing relationships
- **Influence Metrics**: Composite score (citations, velocity, h-index, centrality)
- **Network Analysis**: Cluster detection and centrality calculations
- **External Integration**: Semantic Scholar citation counts
- **Auto-Updates**: Database triggers for real-time count maintenance

## 🤝 Contributing

This project was developed as part of an AI engineering course. Contributions and suggestions are welcome!

## 📄 License

This project is for educational purposes as part of an AI engineering course.

---

**Built with ❤️ for the AI engineering community**
