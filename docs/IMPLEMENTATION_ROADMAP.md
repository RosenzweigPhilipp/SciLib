# SciLib AI Features - Implementation Roadmap

## Branch Strategy & Development Plan

Each feature will be developed in isolation on a dedicated branch, allowing for:
- ✅ Independent testing
- ✅ Incremental merges
- ✅ Easy rollback if needed
- ✅ Parallel development (if time permits)

---

## 🎯 Priority Matrix

### ✅ Completed
1. ✅ pgvector Setup (Branch 1) - Vector database infrastructure
2. ✅ Paper Summarization (Branch 2) - AI-generated paper summaries
3. ✅ Vector Search in Library (Branch 3) - Semantic search foundation
4. ✅ Paper Recommendations (Branch 4) - Multi-strategy internal recommendations

### High Priority (Core Value)
5. External Paper Discovery (Branch 5)
6. Citation Analysis (Branch 6)

### Medium Priority (Enhanced Discovery)
7. Literature Generator (Branch 7)
8. Research Assistant Chat (Branch 8)

### Low Priority (Nice-to-Have)
9. Reading List Optimizer (Branch 9)
10. Auto-tagging (Branch 10)

---

## 📋 Detailed Implementation Plan

---

### **Branch 1: `feature/pgvector-setup`**
**Goal:** Set up vector database infrastructure

**Duration:** 1-2 days  
**Complexity:** Low  
**Dependencies:** None

#### Tasks:
1. **Database Migration**
   - Install `pgvector` extension in PostgreSQL
   - Add migration script to enable extension
   - Test vector operations (insert, query)

2. **Update Paper Model**
   - Add `embedding_title_abstract` column (Vector(1536))
   - Add `embedding_generated_at` timestamp
   - Add database migration

3. **Embedding Generation Service**
   - Create `app/ai/services/embedding_service.py`
   - Implement `generate_embedding(text: str) -> List[float]`
   - Use OpenAI `text-embedding-3-small` model
   - Add error handling and retry logic

4. **Background Task**
   - Create Celery task `generate_paper_embedding_task`
   - Trigger automatically after metadata extraction
   - Allow manual re-generation

5. **Testing**
   - Unit tests for embedding generation
   - Integration test: upload paper → embedding generated
   - Test vector similarity queries

#### Acceptance Criteria:
- [ ] pgvector extension installed and working
- [ ] Papers automatically get embeddings after upload
- [ ] Can query: "SELECT * FROM papers ORDER BY embedding <-> query_vector LIMIT 10"
- [ ] All existing papers can have embeddings regenerated

#### Files to Create/Modify:
- `app/database/migrations/add_pgvector.sql`
- `app/database/models.py` (add Vector column)
- `app/ai/services/embedding_service.py` (new)
- `app/ai/tasks.py` (add embedding task)
- `requirements.txt` (add pgvector, psycopg2 vector support)

---

### **Branch 2: `feature/paper-summarization`**
**Goal:** Generate AI summaries for papers

**Duration:** 2-3 days  
**Complexity:** Low-Medium  
**Dependencies:** None (can work in parallel with Branch 1)

#### Tasks:
1. **Database Schema**
   - Add columns to Paper model:
     - `ai_summary_short` (TEXT)
     - `ai_summary_long` (TEXT)
     - `ai_key_findings` (JSON)
     - `summary_generated_at` (TIMESTAMP)
   - Create migration

2. **Summary Generation Service**
   - Create `app/ai/services/summary_service.py`
   - Implement multi-level summarization:
     - `generate_short_summary()` - 50 words
     - `generate_detailed_summary()` - 200 words
     - `extract_key_findings()` - bullet points
   - Design prompts for each level
   - Handle papers without abstract gracefully

3. **Background Task**
   - Create Celery task `generate_paper_summary_task`
   - Trigger after metadata extraction
   - Allow manual re-summarization

4. **API Endpoints**
   - `POST /api/papers/{id}/summarize` - trigger summarization
   - `GET /api/papers/{id}/summary` - retrieve summaries
   - Add summary fields to paper detail response

5. **Frontend Integration**
   - Add "AI Summary" tab in paper details modal
   - Display short/long summaries and key findings
   - Add "Regenerate Summary" button
   - Loading states during generation

6. **Testing**
   - Test with papers that have abstracts
   - Test with papers without abstracts
   - Test re-summarization
   - Verify prompt quality with sample papers

#### Acceptance Criteria:
- [ ] Papers automatically get summaries after upload
- [ ] UI displays summaries in paper details
- [ ] Summaries are clear and accurate
- [ ] Can manually trigger re-summarization
- [ ] Graceful handling of papers without enough content

#### Files to Create/Modify:
- `app/database/models.py` (add summary columns)
- `app/database/migrations/add_summary_fields.sql`
- `app/ai/services/summary_service.py` (new)
- `app/ai/tasks.py` (add summary task)
- `app/api/papers.py` (add summary endpoints)
- `static/js/components.js` (add summary UI)

---

### **Branch 3: `feature/vector-search`**
**Goal:** Semantic search within user's library

**Duration:** 2-3 days  
**Complexity:** Medium  
**Dependencies:** Branch 1 (`feature/pgvector-setup`)

#### Tasks:
1. **Search Service**
   - Create `app/ai/services/vector_search_service.py`
   - Implement `semantic_search(query: str, limit: int) -> List[Paper]`
   - Generate query embedding
   - Perform cosine similarity search
   - Return ranked results with similarity scores

2. **API Endpoints**
   - `POST /api/search/semantic` - semantic search
     - Request: `{"query": "transformers in NLP", "limit": 10}`
     - Response: Papers with similarity scores
   - Add to existing search endpoint as option

3. **Frontend Integration**
   - Add "Semantic Search" toggle to global search
   - Display similarity scores in results
   - Add search type indicator (keyword vs semantic)
   - Show "No results" with suggestions

4. **Search Quality**
   - Implement hybrid search (combine keyword + semantic)
   - Weight and ranking algorithm
   - Filter by collections/tags
   - Date range filtering

5. **Testing**
   - Test various queries (broad, specific, technical)
   - Compare semantic vs keyword results
   - Test with small library (< 10 papers)
   - Test with larger library

#### Acceptance Criteria:
- [ ] Can search: "papers about neural networks" and get relevant results
- [ ] Semantic search finds papers even with different terminology
- [ ] Results ranked by relevance
- [ ] UI clearly indicates semantic search mode
- [ ] Performance acceptable (< 500ms for 1000 papers)

#### Files to Create/Modify:
- `app/ai/services/vector_search_service.py` (new)
- `app/api/papers.py` (add semantic search endpoint)
- `static/js/main.js` (add semantic search UI)

---

### **Branch 4: `feature/recommendations-internal`**
**Goal:** Recommend similar papers from user's library

**Duration:** 2-3 days  
**Complexity:** Medium  
**Dependencies:** Branch 1 (`feature/pgvector-setup`)

#### Tasks:
1. **Recommendation Engine**
   - Create `app/ai/services/recommendation_service.py`
   - Implement strategies:
     - Vector similarity (primary)
     - Tag-based similarity
     - Collection-based similarity
     - Author-based similarity
   - Combine scores with weights
   - Cache recommendations

2. **Database Schema**
   - Create `Recommendation` table (optional - for caching)
   - Or store in JSON field on Paper model

3. **Background Task**
   - Create Celery task `generate_recommendations_task`
   - Trigger when:
     - New paper added
     - Paper metadata updated
     - User views paper
   - Regenerate periodically (weekly)

4. **API Endpoints**
   - `GET /api/papers/{id}/recommendations` - get similar papers
   - `POST /api/papers/{id}/recommendations/refresh` - regenerate

5. **Frontend Integration**
   - Add "Similar Papers" section in paper details
   - Show top 5 recommendations with scores
   - Display similarity reason (tags, content, author)
   - Click to view recommended paper

6. **Testing**
   - Test with papers in same collection
   - Test with papers by same author
   - Test with papers on similar topics
   - Verify diversity in recommendations

#### Acceptance Criteria:
- [ ] Each paper shows 5 relevant similar papers
- [ ] Recommendations make semantic sense
- [ ] Recommendations update when library grows
- [ ] UI displays similarity reason
- [ ] Performance acceptable (< 300ms)

#### Files to Create/Modify:
- `app/ai/services/recommendation_service.py` (new)
- `app/database/models.py` (add recommendation cache)
- `app/ai/tasks.py` (add recommendation task)
- `app/api/papers.py` (add recommendation endpoints)
- `static/js/components.js` (add recommendations UI)

---

### **Branch 5: `feature/external-discovery`**
**Goal:** Search external APIs for new papers

**Duration:** 3-4 days  
**Complexity:** Medium  
**Dependencies:** Branch 3 (for hybrid internal/external search)

#### Tasks:
1. **Enhanced API Tools**
   - Extend `app/ai/tools/scientific_apis.py`
   - Add semantic search support:
     - Semantic Scholar: use their semantic search API
     - arXiv: enhance query building
     - CrossRef: improve filtering
   - Add pagination support
   - Rate limiting and caching

2. **Discovery Service**
   - Create `app/ai/services/discovery_service.py`
   - Implement `discover_papers(query: str, sources: List[str]) -> List[Dict]`
   - Query multiple sources in parallel
   - Deduplicate results (by DOI/title)
   - Rank by relevance and quality
   - Filter already-in-library papers

3. **API Endpoints**
   - `POST /api/discover` - search external sources
     - Request: `{"query": "transformers", "sources": ["arxiv", "semantic_scholar"], "limit": 20}`
     - Response: Papers with metadata + "add to library" action
   - `POST /api/discover/{result_id}/add` - add discovered paper to library

4. **Frontend Integration**
   - New "Discover" page/section
   - Search interface with source selection
   - Results grid with paper cards
   - "Add to Library" button for each result
   - Show if paper already in library
   - Batch add functionality

5. **Duplicate Detection**
   - Check DOI against library before showing
   - Check title similarity using embeddings
   - Mark duplicates in results

6. **Testing**
   - Test with various queries
   - Test each source individually
   - Test duplicate detection
   - Test adding discovered papers

#### Acceptance Criteria:
- [ ] Can search Semantic Scholar, arXiv, CrossRef
- [ ] Results are relevant and ranked
- [ ] Can add papers directly to library
- [ ] Duplicates are detected and marked
- [ ] Multiple sources work simultaneously
- [ ] Performance acceptable (< 3s for 20 results)

#### Files to Create/Modify:
- `app/ai/tools/scientific_apis.py` (enhance)
- `app/ai/services/discovery_service.py` (new)
- `app/api/discovery.py` (new router)
- `app/main.py` (include discovery router)
- `static/discover.html` (new page)
- `static/js/discovery.js` (new)
- `static/index.html` (add navigation link)

---

### **Branch 6: `feature/literature-generator`**
**Goal:** Generate literature review with gap analysis

**Duration:** 5-7 days  
**Complexity:** High  
**Dependencies:** Branch 5 (`feature/external-discovery`)

#### Tasks:
1. **Query Expansion Service**
   - Create `app/ai/services/query_expansion_service.py`
   - Extract key concepts from user input
   - Generate related terms and synonyms
   - Build comprehensive search queries

2. **Literature Analysis Service**
   - Create `app/ai/services/literature_analysis_service.py`
   - Fetch papers from internal + external sources
   - Group papers by themes
   - Compare approaches
   - Identify research gaps
   - Generate structured output

3. **RAG Implementation**
   - Create `app/ai/services/rag_service.py`
   - Build context from multiple papers
   - Chunking strategy for large contexts
   - Generate synthesis with citations

4. **API Endpoints**
   - `POST /api/literature/generate` - start generation
     - Request: `{"topic": "...", "approach": "...", "contribution": "..."}`
     - Response: Task ID (long-running task)
   - `GET /api/literature/status/{task_id}` - check status
   - `GET /api/literature/result/{task_id}` - get result

5. **Celery Task**
   - Long-running background task
   - Progress updates
   - Error handling
   - Result storage

6. **Frontend Integration**
   - New "Literature Assistant" page
   - Multi-step form:
     - Step 1: Topic and approach
     - Step 2: Key contributions
     - Step 3: Additional filters (year, venues)
   - Progress indicator during generation
   - Results display:
     - Foundational papers
     - Related work
     - Gap analysis
     - Citation suggestions
   - Export functionality (PDF, LaTeX, Markdown)

7. **Testing**
   - Test with various research topics
   - Validate paper categorization
   - Verify gap analysis quality
   - Test with narrow/broad topics

#### Acceptance Criteria:
- [ ] User can describe their research idea
- [ ] System finds relevant papers (internal + external)
- [ ] Papers are categorized appropriately
- [ ] Gap analysis is insightful
- [ ] Output is well-structured
- [ ] Can export results
- [ ] Completion time < 2 minutes

#### Files to Create/Modify:
- `app/ai/services/query_expansion_service.py` (new)
- `app/ai/services/literature_analysis_service.py` (new)
- `app/ai/services/rag_service.py` (new)
- `app/ai/tasks.py` (add literature task)
- `app/api/literature.py` (new router)
- `app/main.py` (include literature router)
- `static/literature.html` (new page)
- `static/js/literature.js` (new)

---

### **Branch 7: `feature/langchain-agents`**
**Goal:** Integrate LangChain for complex orchestration

**Duration:** 4-5 days  
**Complexity:** High  
**Dependencies:** Branch 5 (`feature/external-discovery`)

#### Tasks:
1. **LangChain Tool Wrappers**
   - Create `app/ai/langchain_tools/`
   - Wrap existing tools as LangChain tools:
     - `SemanticScholarSearchTool`
     - `ArxivSearchTool`
     - `InternalVectorSearchTool`
     - `CitationNetworkTool`
   - Standardize input/output formats

2. **Agent Configuration**
   - Create `app/ai/agents/literature_agent.py`
   - Configure OpenAI functions agent
   - Define system prompts
   - Set up tool selection logic

3. **Integrate with Literature Generator**
   - Replace manual orchestration with agent
   - Let agent decide search strategy
   - Agent iteratively refines searches
   - Agent handles multi-step reasoning

4. **Testing**
   - Compare agent vs manual approach
   - Test agent decision-making
   - Verify tool selection is appropriate
   - Monitor token usage

5. **Fallback Strategy**
   - Keep manual orchestration as fallback
   - Switch based on configuration
   - Compare results quality

#### Acceptance Criteria:
- [ ] Agent successfully orchestrates multi-source search
- [ ] Agent makes reasonable tool selections
- [ ] Results quality matches or exceeds manual approach
- [ ] Token usage is acceptable
- [ ] Can toggle between agent and manual mode

#### Files to Create/Modify:
- `app/ai/langchain_tools/` (new directory)
- `app/ai/agents/literature_agent.py` (new)
- `app/ai/services/literature_analysis_service.py` (add agent mode)
- `requirements.txt` (add langchain, langchain-openai)

---

### **Branch 8: `feature/chat-assistant`**
**Goal:** Research assistant chatbot with RAG

**Duration:** 4-5 days  
**Complexity:** Medium-High  
**Dependencies:** Branch 3 (`feature/vector-search`), Branch 7 (optional)

#### Tasks:
1. **Chat Backend**
   - Create `app/ai/services/chat_service.py`
   - Implement conversation management
   - Context window management
   - RAG integration for paper retrieval

2. **Database Schema**
   - Create `ChatSession` and `ChatMessage` tables
   - Store conversation history
   - Link messages to papers used as context

3. **Intent Recognition**
   - Classify query types:
     - Search query
     - Comparison request
     - Summarization request
     - General question
   - Route to appropriate handler

4. **API Endpoints**
   - `POST /api/chat/sessions` - create session
   - `POST /api/chat/sessions/{id}/messages` - send message
   - `GET /api/chat/sessions/{id}/messages` - get history
   - `DELETE /api/chat/sessions/{id}` - end session

5. **Frontend Integration**
   - Floating chat widget
   - Chat interface with message history
   - Typing indicators
   - Paper citations in responses (clickable)
   - Clear conversation button

6. **Response Generation**
   - Use RAG to retrieve relevant papers
   - Generate response with citations
   - Include paper metadata in response
   - Handle follow-up questions

7. **Testing**
   - Test various query types
   - Test conversation continuity
   - Verify paper retrieval accuracy
   - Test citation formatting

#### Acceptance Criteria:
- [ ] Can ask questions about papers in library
- [ ] Maintains conversation context
- [ ] Cites papers in responses
- [ ] Handles various question types
- [ ] Response time < 3s
- [ ] Conversation history persists

#### Files to Create/Modify:
- `app/database/models.py` (add chat tables)
- `app/ai/services/chat_service.py` (new)
- `app/api/chat.py` (new router)
- `app/main.py` (include chat router)
- `static/js/chat.js` (new)
- `static/css/components.css` (add chat styles)

---

### **Branch 9: `feature/citation-graph`**
**Goal:** Visualize citation network

**Duration:** 3-4 days  
**Complexity:** Medium  
**Dependencies:** Branch 5 (for citation data)

#### Tasks:
1. **Citation Data Extraction**
   - Extract citations from Semantic Scholar
   - Store in Paper model (citations_in, citations_out)
   - Build citation network
   - Periodic updates

2. **Graph Service**
   - Create `app/ai/services/graph_service.py`
   - Build citation graph from library
   - Calculate graph metrics:
     - Degree centrality (hub papers)
     - Betweenness (bridge papers)
     - Connected components
   - Generate graph data for visualization

3. **API Endpoints**
   - `GET /api/graph/citation` - get citation graph
   - `GET /api/papers/{id}/citations` - get paper's citations
   - `GET /api/graph/metrics` - get graph statistics

4. **Frontend Visualization**
   - New "Citation Network" page
   - Interactive graph using D3.js or vis.js
   - Node: Paper (size = citation count)
   - Edge: Citation relationship
   - Zoom, pan, drag nodes
   - Click node to view paper details
   - Highlight connected papers

5. **Features**
   - Filter by date range
   - Filter by collection/tag
   - Show only connected component
   - Identify "hub" papers
   - Export graph as image

#### Acceptance Criteria:
- [ ] Graph displays all papers in library
- [ ] Citation relationships are accurate
- [ ] Interactive and performant
- [ ] Identifies important papers
- [ ] Export functionality works

#### Files to Create/Modify:
- `app/database/models.py` (add citation fields)
- `app/ai/services/graph_service.py` (new)
- `app/api/graph.py` (new router)
- `static/graph.html` (new page)
- `static/js/graph.js` (new)
- `requirements.txt` (add networkx if needed)

---

### **Branch 10: `feature/auto-tagging`**
**Goal:** Automatic tag suggestions and collection assignment

**Duration:** 2-3 days  
**Complexity:** Low-Medium  
**Dependencies:** Branch 2 (`feature/paper-summarization`)

#### Tasks:
1. **Tag Extraction Service**
   - Create `app/ai/services/tagging_service.py`
   - Extract key topics from paper using LLM
   - Match with existing tags
   - Suggest new tags
   - Suggest collections

2. **API Endpoints**
   - `POST /api/papers/{id}/suggest-tags` - get tag suggestions
   - `POST /api/papers/{id}/auto-tag` - apply suggestions

3. **Frontend Integration**
   - Show tag suggestions in paper edit modal
   - "Auto-tag" button
   - Accept/reject individual suggestions
   - Create new tags from suggestions

4. **Batch Operations**
   - Auto-tag all papers
   - Auto-tag papers in collection
   - Progress tracking

#### Acceptance Criteria:
- [ ] Generates relevant tag suggestions
- [ ] Can auto-tag individual papers
- [ ] Can batch auto-tag all papers
- [ ] User can accept/reject suggestions
- [ ] New tags can be created from suggestions

#### Files to Create/Modify:
- `app/ai/services/tagging_service.py` (new)
- `app/api/papers.py` (add tagging endpoints)
- `static/js/components.js` (add tag suggestions UI)

---

## 🔄 Merge Strategy

### After Each Branch:
1. **Code Review**
   - Self-review all changes
   - Check for code quality issues
   - Verify tests pass

2. **Testing**
   - Run all existing tests
   - Test new feature thoroughly
   - Test integration with existing features

3. **Documentation**
   - Update API documentation
   - Update user guide
   - Add inline code comments

4. **Merge to Main**
   - Create pull request
   - Merge when tests pass
   - Tag release (optional: `v1.1.0`, `v1.2.0`, etc.)

5. **Deploy**
   - Deploy to production (if applicable)
   - Monitor for issues
   - Gather user feedback

---

## 📊 Progress Tracking

Create a simple tracking board:

```
| Branch | Status | Started | Completed | Notes |
|--------|--------|---------|-----------|-------|
| feature/pgvector-setup | ⬜ Not Started | - | - | Foundation |
| feature/paper-summarization | ⬜ Not Started | - | - | High value |
| feature/vector-search | ⬜ Not Started | - | - | Depends on #1 |
| feature/recommendations-internal | ⬜ Not Started | - | - | Depends on #1 |
| feature/external-discovery | ⬜ Not Started | - | - | - |
| feature/literature-generator | ⬜ Not Started | - | - | Complex |
| feature/langchain-agents | ⬜ Not Started | - | - | Optional |
| feature/chat-assistant | ⬜ Not Started | - | - | Complex |
| feature/citation-graph | ⬜ Not Started | - | - | Nice-to-have |
| feature/auto-tagging | ⬜ Not Started | - | - | Low priority |
```

Update status:
- ⬜ Not Started
- 🔨 In Progress
- ✅ Completed
- ⚠️ Blocked
- ❌ Cancelled

---

## ⚡ Quick Wins (Optional Branches)

If you want smaller victories along the way:

### **Branch A: `feature/reading-tracker`**
- Add "Mark as Read/Unread" functionality
- Reading priority levels
- Reading queue view
- **Duration:** 1 day

### **Branch B: `feature/export-improvements`**
- Export papers with summaries
- BibTeX export improvements
- Batch export functionality
- **Duration:** 1-2 days

### **Branch C: `feature/ui-polish`**
- Better loading states
- Error messages
- Animations and transitions
- Dark mode
- **Duration:** 2-3 days

---

## 🎓 Learning Path

As you implement each branch, you'll learn:

1. **pgvector-setup**: Vector databases, embeddings
2. **paper-summarization**: Prompt engineering, LLM usage
3. **vector-search**: Similarity search, ranking algorithms
4. **recommendations**: Recommendation systems, scoring
5. **external-discovery**: API integration, parallel requests
6. **literature-generator**: RAG, complex workflows
7. **langchain-agents**: Agent frameworks, tool selection
8. **chat-assistant**: Conversational AI, context management
9. **citation-graph**: Graph theory, network analysis
10. **auto-tagging**: Classification, NLP

---

## 💡 Tips for Success

1. **Start Small**: Begin with Branch 1 (pgvector-setup) - it's foundational but manageable

2. **Test Early**: Don't wait until feature is complete to test

3. **Document As You Go**: Update docs immediately, while it's fresh

4. **Commit Frequently**: Small, atomic commits with clear messages

5. **Use Feature Flags**: Enable/disable features via config without code changes

6. **Monitor Costs**: Track OpenAI API usage as features accumulate

7. **Get Feedback**: Test with real papers, adjust based on results

8. **Don't Over-Engineer**: MVP first, polish later

9. **Reuse Code**: Many services will share patterns (error handling, retry logic)

10. **Stay Focused**: One branch at a time, resist scope creep

---

## 🎯 Success Metrics

After completing each branch, evaluate:

- ✅ **Functionality**: Does it work as intended?
- ✅ **Performance**: Response times acceptable?
- ✅ **Accuracy**: Results are relevant/correct?
- ✅ **UX**: Easy to use, intuitive?
- ✅ **Cost**: API usage within budget?
- ✅ **Maintainability**: Code is clean, tested, documented?

---

## 🚀 Recommended Starting Order

Based on value, dependencies, and complexity:

1. **Start Here**: `feature/pgvector-setup` (foundation, required for most features)
2. **Quick Win**: `feature/paper-summarization` (immediate value, no dependencies)
3. **Build On**: `feature/vector-search` (requires #1, high value)
4. **Extend**: `feature/recommendations-internal` (requires #1, moderate value)
5. **Expand**: `feature/external-discovery` (standalone, high value)
6. **Advanced**: Choose between:
   - `feature/literature-generator` (if you need paper writing help)
   - `feature/chat-assistant` (if you want interactive exploration)
7. **Polish**: Add remaining features based on needs

---

Good luck! Start with Branch 1 when you're ready to code. Each branch is designed to be completable in a few days and provides incremental value to the system.
