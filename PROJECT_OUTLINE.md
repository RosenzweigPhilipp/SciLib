# SciLib - AI-Powered Scientific Literature Manager

## Project Overview

SciLib is an AI-powered scientific literature manager designed for researchers, students, and academics. It combines the organizational capabilities of reference managers like Mendeley or Zotero with modern AI tooling to accelerate literature discovery, comprehension, and cross-paper insight.

## Architecture

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JavaScript
- **AI Integration**: LangChain + LangSmith (Phase 2)
- **Authentication**: API Key based
- **Version Control**: Git with feature branches

## Development Phases

### Phase 1: Core Infrastructure (Current)
1. **Project Setup & Documentation**
   - Initialize project structure
   - Setup development environment
   - Create comprehensive documentation

2. **Backend Foundation**
   - FastAPI application setup
   - Configuration management
   - API key authentication middleware
   - Basic health checks and API structure

3. **Database Layer**
   - PostgreSQL setup and connection
   - Database models using SQLAlchemy
   - Migration system
   - CRUD operations

4. **Frontend Foundation**
   - Static HTML/CSS interface
   - JavaScript for API communication
   - Responsive design
   - File upload interface

### Phase 2: Core Features
5. **Library Management System**
   - PDF upload and storage
   - Metadata extraction pipeline
   - Collections and folder organization
   - Tagging system
   - Search functionality

6. **Content Processing**
   - PDF text extraction
   - Metadata parsing (title, authors, abstract, etc.)
   - Full-text indexing
   - File management system

### Phase 3: AI Integration
7. **AI-Powered Insights**
   - LangChain integration
   - Document summarization
   - Key points extraction
   - ELI5 explanations
   - Author profiling

8. **RAG System**
   - Vector database setup
   - Document embedding pipeline
   - Semantic search
   - Chat interface for Q&A

9. **Discovery & Recommendations**
   - Semantic similarity matching
   - Related papers suggestions
   - Topic clustering
   - External API integration (CrossRef, Semantic Scholar)

## Detailed Feature Specifications

### A. Library Management
**Purpose**: Organize and manage scientific papers in a user-friendly interface

**Features**:
- **PDF Upload**: Drag-and-drop or file picker interface
- **Automatic Metadata Extraction**: 
  - Parse PDF metadata and content
  - Extract title, authors, abstract, keywords
  - Identify publication year, journal, DOI
- **Organization System**:
  - User-defined collections/folders
  - Custom tagging with auto-suggestions
  - Hierarchical organization
- **Search Capabilities**:
  - Full-text search across all documents
  - Metadata-based filtering
  - Advanced search with multiple criteria
  - Search result ranking and relevance

### B. AI-Powered Paper Insights
**Purpose**: Provide intelligent analysis and summaries of research papers

**Features**:
- **Multi-Level Summaries**:
  - Abstract summarization (condensed version)
  - Detailed summary (methodology, results, conclusions)
  - ELI5 explanations (simplified for broader audience)
- **Content Analysis**:
  - Key contributions identification
  - Research gaps and limitations analysis
  - Methodology extraction
  - Results interpretation
- **Research Facilitation**:
  - Suggested follow-up questions
  - Research direction recommendations
  - Methodology applicability assessment
- **Author Intelligence**:
  - Author profile generation
  - Publication history analysis
  - Research focus identification

### C. Discovery & Recommendation System
**Purpose**: Help users discover relevant literature and research connections

**Features**:
- **Semantic Similarity**:
  - Related papers based on content similarity
  - Cross-reference analysis
  - Citation network exploration
- **Author-Based Discovery**:
  - Other papers by same authors
  - Collaborator networks
  - Author expertise mapping
- **Personalized Recommendations**:
  - "You may also like" suggestions
  - Based on reading history and preferences
  - Trending papers in user's research areas
- **Content Clustering**:
  - Automatic topic detection
  - Research theme identification
  - Library organization suggestions

### D. RAG-Powered Chat Interface
**Purpose**: Enable natural language interaction with the user's research library

**Features**:
- **Multi-Paper Analysis**:
  - Cross-paper comparisons
  - Theme analysis across multiple documents
  - Synthesis of findings
- **Targeted Queries**:
  - Tag-based paper filtering for queries
  - Time-based analysis (recent vs. historical papers)
  - Author-specific insights
- **Research Assistance**:
  - Methodology comparisons
  - Result synthesis
  - Gap identification
  - Research direction suggestions

## Technical Implementation Strategy

### Database Schema (Phase 1)
```sql
-- Core entities
Papers: id, title, authors, abstract, keywords, year, journal, doi, file_path, created_at, updated_at
Collections: id, name, description, created_at, updated_at
Tags: id, name, color, created_at
PaperCollections: paper_id, collection_id
PaperTags: paper_id, tag_id
```

### API Endpoints (Phase 1)
```
POST /api/papers/upload          # Upload new paper
GET /api/papers                  # List papers with pagination/filtering
GET /api/papers/{id}             # Get specific paper details
PUT /api/papers/{id}             # Update paper metadata
DELETE /api/papers/{id}          # Delete paper

GET /api/collections             # List collections
POST /api/collections            # Create collection
PUT /api/collections/{id}        # Update collection
DELETE /api/collections/{id}     # Delete collection

GET /api/tags                    # List tags
POST /api/tags                   # Create tag
PUT /api/tags/{id}               # Update tag
DELETE /api/tags/{id}            # Delete tag

GET /api/search                  # Search papers
GET /api/health                  # Health check
```

### Frontend Structure (Phase 1)
```
static/
├── css/
│   ├── main.css
│   └── components.css
├── js/
│   ├── main.js
│   ├── api.js
│   └── components.js
├── index.html
└── assets/
```

## Development Workflow

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/backend-setup`: Backend infrastructure
- `feature/database-setup`: Database implementation
- `feature/frontend-init`: Frontend foundation
- `feature/ai-integration`: AI features (Phase 2)

### Commit Strategy
Each major milestone gets its own commit and push:
1. Project initialization and documentation
2. FastAPI backend setup
3. Database models and CRUD operations
4. Frontend foundation
5. Integration and testing

### Quality Assurance
- Code review for each feature branch
- Testing before merging to develop
- Documentation updates with each feature
- Regular refactoring and optimization

## Future Enhancements (Post-Course)
- User authentication and multi-tenancy
- Real-time collaboration features
- Advanced AI models and fine-tuning
- Mobile application
- Integration with external research databases
- Export capabilities (BibTeX, EndNote, etc.)
- Advanced analytics and research insights

## Success Metrics
- Successful paper upload and metadata extraction
- Functional CRUD operations on all entities
- Responsive and intuitive user interface
- Working AI-powered summarization and chat
- Effective search and recommendation system
- Clean, maintainable codebase with proper documentation