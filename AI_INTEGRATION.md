# SciLib AI Integration Documentation

## Overview

SciLib now features a comprehensive AI-powered metadata extraction system that automatically processes uploaded PDF papers to extract bibliographic information for BibTeX generation.

## Architecture

### Three-Stage AI Pipeline

1. **PDF Extraction Agent**
   - Extracts text content using multiple methods (direct text + OCR fallback)
   - Identifies title, authors, abstract, keywords from PDF content
   - Provides confidence scoring for extraction quality

2. **Metadata Search Agent** 
   - Searches scientific databases (CrossRef, arXiv, Semantic Scholar)
   - Falls back to semantic web search via Exa.ai
   - Cross-references and validates information

3. **Validation Agent**
   - Merges results from all sources
   - Resolves conflicts between data sources
   - Generates complete BibTeX entries
   - Assigns final confidence scores

### Two-Tier Processing

- **Fast Extraction**: Initial processing for immediate results
- **High Confidence Threshold**: Papers below threshold get orange triangle indicator
- **Background Re-processing**: Low confidence papers automatically queued for enhanced processing

## API Endpoints

### Start Extraction
```http
POST /api/ai/extract/{paper_id}
```
Triggers background metadata extraction for a paper.

### Check Status  
```http
GET /api/ai/status/{task_id}
```
Returns real-time extraction progress and status.

### Get Results
```http
GET /api/ai/paper/{paper_id}/extraction
```
Retrieves complete extraction results and metadata.

### Approve/Reject
```http
POST /api/ai/paper/{paper_id}/approve
POST /api/ai/paper/{paper_id}/reject
```
User approval workflow for AI-extracted metadata.

### Health Check
```http
GET /api/ai/health
```
System health status for AI services.

## Configuration

### Required Environment Variables

```bash
# OpenAI API (Required)
OPENAI_API_KEY=sk-your-openai-api-key

# Database  
DATABASE_URL=postgresql://user:pass@localhost/scilib

# Redis for background tasks
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379

# Optional: Enhanced search capabilities
EXA_API_KEY=your-exa-api-key
SEMANTIC_SCHOLAR_API_KEY=your-s2-api-key
CROSSREF_EMAIL=your-email@domain.com
```

### Optional Configuration

```bash
# PDF Processing
MAX_OCR_PAGES=10
OCR_LANGUAGE=eng
EXTRACTION_TIMEOUT=300

# File Upload
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50000000
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install System Dependencies

**macOS:**
```bash
brew install redis tesseract
```

**Ubuntu:**
```bash
sudo apt install redis-server tesseract-ocr
```

### 3. Configure Environment

Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Start Services

**Option A: Full Stack (Recommended)**
```bash
./start_scilib.sh
```

**Option B: Manual Start**
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker  
python celery_worker.py

# Terminal 3: Start API Server
uvicorn app.main:app --reload
```

## Usage Workflow

### 1. Upload Paper
- User uploads PDF via web interface
- Paper record created in database
- Extraction automatically triggered

### 2. Monitor Progress
- Real-time progress updates via WebSocket/polling
- Status indicators: Processing → Complete/Failed
- Orange triangle for low confidence results

### 3. Review & Approve
- View extracted metadata in web interface
- Compare against original PDF
- Approve or reject AI suggestions
- Manual editing for corrections

### 4. Export BibTeX
- Generate complete BibTeX entries
- Include AI extraction confidence scores
- Export individual papers or collections

## Confidence Scoring

### Scoring Factors

- **Source Reliability** (40%): CrossRef > Semantic Scholar > arXiv > Web Search
- **Field Completeness** (30%): Required vs optional metadata fields
- **Cross-Validation** (20%): Agreement between multiple sources  
- **Format Validation** (10%): Proper DOI format, reasonable years, etc.

### Confidence Thresholds

- **≥ 80%**: High confidence - Auto-approve
- **60-79%**: Medium confidence - Review recommended
- **40-59%**: Low confidence - Manual verification required  
- **< 40%**: Very low confidence - Orange triangle indicator

## Scientific APIs Integration

### CrossRef
- Free DOI-based metadata lookup
- Comprehensive journal article information
- Rate limited: 50 requests/second

### arXiv
- Preprint server integration
- Full text search capabilities
- Categories and subject classification

### Semantic Scholar
- Academic graph database
- Citation networks and influence metrics
- Optional API key for enhanced features

### Exa.ai
- Semantic web search fallback
- Domain-filtered academic sources
- Natural language query processing

## Background Processing

### Celery Tasks

- **PDF Text Extraction**: Multi-method content extraction
- **Metadata Enrichment**: API searches and validation
- **Quality Assurance**: Confidence scoring and conflict resolution
- **Database Updates**: Atomic result storage

### Queue Management

- **Default Queue**: Standard extraction tasks
- **Priority Queue**: Re-processing low confidence papers
- **Cleanup Tasks**: Periodic maintenance and cleanup

### Monitoring

```bash
# Check Celery worker status
celery -A app.ai.tasks inspect active

# Monitor queue lengths
celery -A app.ai.tasks inspect reserved

# View task history
celery -A app.ai.tasks events
```

## Error Handling

### Common Issues

1. **PDF Extraction Failures**
   - Scanned documents without text layer
   - Password-protected files
   - Corrupted or malformed PDFs

2. **API Rate Limits**
   - Automatic retry with exponential backoff
   - Queue management to respect limits
   - Fallback to alternative sources

3. **Network Timeouts**
   - Configurable timeout settings
   - Graceful degradation to cached results
   - Error logging and alerting

### Recovery Mechanisms

- **Automatic Retries**: Up to 3 attempts for transient failures
- **Partial Results**: Return best available data on partial failure
- **Manual Retry**: User-initiated re-processing for failed extractions
- **Fallback Sources**: Alternative APIs when primary sources fail

## Performance Optimization

### Caching Strategy

- **API Response Caching**: Redis cache for repeated queries
- **PDF Content Caching**: Avoid re-extraction of same documents
- **Metadata Validation**: Cache validation rules and patterns

### Scaling Considerations

- **Horizontal Scaling**: Multiple Celery workers across machines
- **Database Optimization**: Indexes on extraction status fields
- **CDN Integration**: Static file serving for uploaded papers

## Security & Privacy

### Data Protection

- **API Key Security**: Environment variable storage only
- **File Access Control**: User-based permission checking
- **Audit Logging**: Complete extraction activity logs

### Rate Limiting

- **API Quota Management**: Track usage across all integrated services
- **User-Level Limits**: Prevent abuse of extraction resources
- **Graceful Degradation**: Continue with available services when limits hit

## Testing

### Unit Tests
```bash
pytest tests/ai/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Load Testing
```bash
# Start test worker
celery -A app.ai.tasks worker --concurrency=1

# Run extraction load test
python tests/load_test_extraction.py
```

## Troubleshooting

### Common Problems

**Celery worker not starting:**
```bash
# Check Redis connectivity
redis-cli ping

# Verify Python path
echo $PYTHONPATH

# Check for port conflicts
lsof -i :6379
```

**PDF extraction failures:**
```bash
# Test tesseract installation
tesseract --version

# Check file permissions
ls -la uploads/

# Verify PDF integrity
python -c "import PyMuPDF; print('PyMuPDF working')"
```

**API authentication errors:**
```bash
# Verify environment variables
env | grep -E "(OPENAI|EXA|SEMANTIC)"

# Test API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### Debug Mode

Enable detailed logging:
```bash
export PYTHONPATH=.:$PYTHONPATH
export CELERY_LOG_LEVEL=DEBUG
python celery_worker.py
```

## Contributing

### Development Setup

1. Fork repository
2. Create feature branch: `git checkout -b feature/ai-enhancement`
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `pytest`
5. Submit pull request

### Code Style

- Follow PEP 8 conventions
- Use type hints for all functions
- Add docstrings for all public methods
- Maximum line length: 100 characters

### Testing Requirements

- Unit test coverage > 80%
- Integration tests for all API endpoints
- Mock external API calls in tests
- Document test scenarios in docstrings

---

## Support

For issues and questions:
- GitHub Issues: [Create Issue](https://github.com/your-repo/scilib/issues)
- Documentation: [Full Docs](https://scilib.readthedocs.io)
- Email: support@scilib.com