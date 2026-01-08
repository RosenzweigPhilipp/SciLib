# RAG Q&A Search Feature

## Overview

The RAG (Retrieval-Augmented Generation) Q&A search feature allows users to ask natural language questions about their paper library and receive AI-generated answers based on the actual content of their papers.

## Architecture

### Backend Components

1. **RAG Service** (`app/ai/services/rag_service.py`)
   - Core RAG logic for question answering
   - Retrieves relevant papers via semantic search
   - Generates answers using GPT-4o-mini with paper context
   - Includes query enhancement capabilities

2. **Search API Endpoint** (`app/api/search.py`)
   - New `/api/search/qa` POST endpoint
   - Accepts question and optional filters
   - Returns answer with source citations

### Frontend Components

1. **UI Toggle** (in header)
   - Mode switcher between regular search and Q&A
   - Updates search placeholder text
   - Visual indication of active mode

2. **Q&A Results Modal**
   - Displays question, answer, and source papers
   - Shows relevance scores for each source
   - Allows clicking through to paper details

3. **API Client** (`static/js/api.js`)
   - `API.ai.askQuestion()` method for Q&A requests
   - Handles request formatting and error handling

## Usage

### User Workflow

1. **Switch to Q&A Mode**
   - Click the robot icon (🤖) in the header search area
   - Search placeholder changes to "Ask a question about your papers..."

2. **Ask a Question**
   - Type a natural language question
   - Press Enter to submit
   - Examples:
     - "How do transformers improve machine translation?"
     - "What are the main challenges in computer vision?"
     - "What methods are used for sentiment analysis?"

3. **View Results**
   - Modal displays with AI-generated answer
   - Source papers listed with relevance scores
   - Click any source to view full paper details

### API Usage

**Endpoint:** `POST /api/search/qa`

**Request:**
```json
{
  "question": "How do attention mechanisms work?",
  "max_papers": 5,
  "collection_ids": [1, 2],
  "tag_ids": [5],
  "year_from": 2020,
  "year_to": 2024
}
```

**Response:**
```json
{
  "question": "How do attention mechanisms work?",
  "answer": "According to Paper 1, attention mechanisms...",
  "sources": [
    {
      "paper_id": 123,
      "title": "Attention Is All You Need",
      "authors": "Vaswani et al.",
      "year": 2017,
      "relevance_score": 0.89,
      "doi": "...",
      "journal": "NeurIPS"
    }
  ],
  "context_papers_count": 3,
  "has_sources": true
}
```

## Technical Details

### RAG Pipeline

1. **Retrieval Phase**
   - Uses existing semantic search via pgvector
   - Finds top K most relevant papers (default: 5)
   - Filters by collections, tags, year range if specified
   - Minimum relevance threshold: 0.3

2. **Context Building**
   - Extracts title, authors, year, journal
   - Uses AI summary (long > short) if available
   - Falls back to abstract if no summary
   - Includes keywords for additional context
   - Formats as structured context for LLM

3. **Generation Phase**
   - Uses GPT-4o-mini for cost efficiency
   - System prompt emphasizes:
     - Answer only from provided papers
     - Cite papers explicitly in answer
     - Acknowledge disagreements between papers
     - Be clear when information is insufficient
   - Temperature: 0.3 (more factual, less creative)
   - Max tokens: 1000

### Cost Estimation

- **Per Question:** ~$0.001-0.005
- Based on:
  - 5 papers × ~500 tokens context = 2,500 tokens
  - 1,000 max output tokens
  - GPT-4o-mini pricing: $0.15/$0.60 per 1M tokens (in/out)

### Error Handling

- **No relevant papers:** Returns message indicating no sources found
- **API failures:** Graceful error messages to user
- **Empty queries:** Validation prevents empty questions
- **LLM errors:** Caught and reported with context

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for LLM generation (already configured)
- No additional configuration needed

### Tunable Parameters

In `RAGService.__init__()`:
- `max_context_papers`: Default 5, adjustable per request
- `max_tokens`: Default 1000 for answer length
- `model`: Currently "gpt-4o-mini"

In `answer_question()` method:
- `min_score`: Minimum relevance threshold (0.3)

## Future Enhancements

### Potential Improvements

1. **Streaming Responses**
   - Stream LLM output token-by-token
   - Better UX for long answers
   - Requires WebSocket or SSE support

2. **Citation Formatting**
   - Parse LLM output for "[Paper N]" markers
   - Make citations clickable inline
   - Show source on hover

3. **Follow-up Questions**
   - Maintain conversation context
   - "Tell me more about..." support
   - Session-based chat history

4. **Multi-turn Conversations**
   - Store conversation history
   - Context-aware follow-ups
   - Clarification questions

5. **Enhanced Query Understanding**
   - Use `generate_enhanced_query()` for vague questions
   - Automatic query expansion
   - Synonym detection

6. **Context-Aware Discovery**
   - Integrate with external discovery
   - "Find papers that answer..." → external search
   - Hybrid internal/external answering

### Advanced Features

1. **Evidence Highlighting**
   - Extract specific quotes from papers
   - Show exact passages used for answer
   - Direct PDF links to relevant sections

2. **Answer Quality Scoring**
   - Confidence metrics for answers
   - Source agreement analysis
   - Flag when papers contradict

3. **Custom System Prompts**
   - User-configurable answer style
   - Domain-specific instructions
   - Persona options (technical, simple, etc.)

## Testing

### Manual Testing

1. Start server: `./start_scilib.sh`
2. Upload papers with diverse topics
3. Test questions in UI Q&A mode
4. Verify source citations are accurate

### Automated Testing

Run test suite:
```bash
python minimals/test_rag_qa.py
```

Tests cover:
- Basic Q&A with various questions
- Filter application (year, collections, tags)
- Edge cases (no relevant papers)
- Error handling

## Troubleshooting

### "No relevant papers found"
- Check if papers have embeddings generated
- Verify question relates to paper topics
- Lower `min_score` threshold if needed

### "Failed to generate answer"
- Check `OPENAI_API_KEY` is set
- Verify API key has credits
- Check server logs for detailed errors

### Slow responses
- Normal: 3-10 seconds per question
- Depends on: number of papers, context size, LLM speed
- Consider caching for repeated questions

### Poor answer quality
- Ensure papers have good abstracts/summaries
- Check relevance scores of sources used
- May need more/better papers on topic

## Comparison with Traditional Search

| Feature | Traditional Search | RAG Q&A Search |
|---------|-------------------|----------------|
| Input | Keywords/phrases | Natural language questions |
| Output | List of papers | Synthesized answer + sources |
| Processing | Vector similarity | Semantic search + LLM generation |
| Cost | Free (local) | ~$0.003 per query (LLM) |
| Speed | <100ms | 3-10 seconds |
| Use Case | Finding papers | Understanding concepts |

## Related Documentation

- [AI Integration Guide](AI_INTEGRATION.md) - Overall AI architecture
- [Vector Search](vector_search_service.py) - Retrieval component
- [Embedding Service](embedding_service.py) - Vector generation
- [Search API](../api/search.py) - All search endpoints
