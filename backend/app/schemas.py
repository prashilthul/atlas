from typing import Optional

from pydantic import BaseModel


class SectionSchema(BaseModel):
    heading: str
    level: int
    content: str
    order_index: int


class CitationSchema(BaseModel):
    marker: str
    context: str


class ReferenceSchema(BaseModel):
    marker: str
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    raw_text: str


class PaperSchema(BaseModel):
    title: str
    authors: list[str]
    abstract: Optional[str] = None
    year: Optional[int] = None
    source_url: Optional[str] = None
    sections: list[SectionSchema] = []
    citations: list[CitationSchema] = []
    references: list[ReferenceSchema] = []
