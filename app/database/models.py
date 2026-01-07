from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .connection import Base


# Association tables for many-to-many relationships
paper_collections = Table(
    'paper_collections',
    Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id'), primary_key=True),
    Column('collection_id', Integer, ForeignKey('collections.id'), primary_key=True)
)

paper_tags = Table(
    'paper_tags',
    Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    authors = Column(Text, nullable=False)
    abstract = Column(Text)
    keywords = Column(Text)
    year = Column(Integer, index=True)
    journal = Column(String(255))
    doi = Column(String(255), unique=True, index=True)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # BibTeX/Citation fields (for proper academic citations)
    publisher = Column(String(255))           # Publisher name
    volume = Column(String(50))               # Journal volume
    issue = Column(String(50))                # Journal issue/number
    pages = Column(String(50))                # Page range (e.g., "123-145")
    booktitle = Column(String(500))           # Conference/book title
    series = Column(String(255))              # Series name
    edition = Column(String(50))              # Edition (for books)
    isbn = Column(String(50))                 # ISBN (for books)
    url = Column(String(500))                 # Canonical URL
    month = Column(Integer)                   # Publication month (1-12)
    note = Column(Text)                       # Additional notes
    publication_type = Column(String(50))     # article, inproceedings, book, etc.
    
    # AI Extraction fields
    extraction_status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    extraction_confidence = Column(Float, default=0.0)  # 0.0 to 1.0
    extraction_sources = Column(JSON, default=dict)  # Which APIs provided data
    extraction_metadata = Column(JSON, default=dict)  # Raw extraction results
    extracted_at = Column(DateTime(timezone=True))
    manual_override = Column(Boolean, default=False)  # User can override AI extraction
    
    # Embedding fields for vector search
    embedding_title_abstract = Column(Vector(1536))  # OpenAI text-embedding-3-small
    embedding_generated_at = Column(DateTime(timezone=True))
    
    # AI Summary fields
    ai_summary_short = Column(Text)  # ~50 word summary
    ai_summary_long = Column(Text)  # ~200 word detailed summary
    ai_summary_eli5 = Column(Text)  # Explain Like I'm 5 - simple explanation
    ai_key_findings = Column(JSON)  # List of key findings/bullet points
    summary_generated_at = Column(DateTime(timezone=True))
    summary_generation_method = Column(String(50))  # 'llm_knowledge', 'full_extraction', 'manual'
    
    # LLM Knowledge Check fields
    llm_knowledge_check = Column(Boolean)  # True if LLM knows paper, False if not, None if not checked
    llm_knowledge_confidence = Column(Float)  # 0.0-1.0 confidence score
    llm_knowledge_checked_at = Column(DateTime(timezone=True))
    
    # Citation fields
    citation_count = Column(Integer, default=0, index=True)  # Times cited by other library papers
    reference_count = Column(Integer, default=0)  # Papers this paper cites in library
    external_citation_count = Column(Integer, default=0)  # Total citations from external sources
    h_index = Column(Integer, default=0, index=True)  # H-index based on library citations
    influence_score = Column(Float, default=0.0, index=True)  # Calculated influence (0.0-1.0)
    citations_updated_at = Column(DateTime(timezone=True))
    
    # Relationships
    collections = relationship("Collection", secondary=paper_collections, back_populates="papers")
    tags = relationship("Tag", secondary=paper_tags, back_populates="papers")
    
    # Citation relationships
    citations_made = relationship(
        "Citation",
        foreign_keys="Citation.citing_paper_id",
        back_populates="citing_paper",
        cascade="all, delete-orphan"
    )
    citations_received = relationship(
        "Citation",
        foreign_keys="Citation.cited_paper_id",
        back_populates="cited_paper",
        cascade="all, delete-orphan"
    )


class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    is_smart = Column(Boolean, default=False, index=True)  # Auto-generated by AI
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    papers = relationship("Paper", secondary=paper_collections, back_populates="collections")


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7), default="#007bff")  # Hex color code
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships  
    papers = relationship("Paper", secondary=paper_tags, back_populates="tags")


class Citation(Base):
    __tablename__ = "citations"
    
    id = Column(Integer, primary_key=True, index=True)
    citing_paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    cited_paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    context = Column(Text)  # Optional: citation context from text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    citing_paper = relationship("Paper", foreign_keys=[citing_paper_id], back_populates="citations_made")
    cited_paper = relationship("Paper", foreign_keys=[cited_paper_id], back_populates="citations_received")


# Compatibility aliases for association tables
PaperCollection = paper_collections
PaperTag = paper_tags


class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @staticmethod
    def get(db, key: str, default=None):
        """Get a setting value by key."""
        setting = db.query(Settings).filter(Settings.key == key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(db, key: str, value):
        """Set a setting value."""
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value)
            db.add(setting)
        db.commit()
        return setting
