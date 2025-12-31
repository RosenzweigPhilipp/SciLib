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
    ai_key_findings = Column(JSON)  # List of key findings/bullet points
    summary_generated_at = Column(DateTime(timezone=True))
    
    # Relationships
    collections = relationship("Collection", secondary=paper_collections, back_populates="papers")
    tags = relationship("Tag", secondary=paper_tags, back_populates="papers")


class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
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


# Compatibility aliases for association tables
PaperCollection = paper_collections
PaperTag = paper_tags