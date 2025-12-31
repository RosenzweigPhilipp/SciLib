# SciLib - AI-Powered Scientific Literature Manager

A modern web application for managing and organizing scientific literature with AI integration capabilities.

## 🚀 Features

- **Paper Management**: Upload, view, edit, and delete PDF papers
- **Secure Authentication**: Session-based authentication system (no hardcoded API keys)
- **Collections & Tags**: Organize papers into collections and tag them
- **Search & Filter**: Search papers by title, authors, or content
- **Dashboard**: Overview of your literature collection with statistics
- **Responsive UI**: Modern, clean interface that works on desktop and mobile

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Authentication**: JWT-like session tokens
- **File Upload**: PDF processing and storage

## ⚡ Quick Start

### Prerequisites

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

5. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb scilib_db
   
   # The app will auto-create tables on first run
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the application**
   - Open http://localhost:8000
   - Enter your API key from the .env file to login

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
```

## 🚧 Development Roadmap

**Project Phase**: AI Integration Complete ✅

### Phase 1: Core Infrastructure ✅ COMPLETE
- ✅ Backend API with FastAPI
- ✅ PostgreSQL database with SQLAlchemy ORM
- ✅ File upload and PDF storage system
- ✅ Frontend interface with CRUD operations
- ✅ Session-based authentication with X-API-Key
- ✅ Paper, collection, and tag management

### Phase 2: AI Integration ✅ COMPLETE

#### Branch 1: Vector Database Setup ✅
- ✅ PostgreSQL pgvector extension
- ✅ Vector embedding storage
- ✅ Similarity search infrastructure

#### Branch 2: Paper Summarization ✅
- ✅ AI-powered paper summaries (short/long/key findings)
- ✅ OpenAI GPT-4o-mini integration
- ✅ Background processing with Celery
- ✅ PDF text extraction pipeline

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
