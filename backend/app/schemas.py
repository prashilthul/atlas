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


class PaperResponse(BaseModel):
    id: str
    title: str
    authors: list[str]
    chunk_count: int
    status: str


class PaperStatus(BaseModel):
    id: str
    status: str
    error: str | None = None


class SectionInfo(BaseModel):
    heading: str
    level: int
    order_index: int


class PaperListItem(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int | None
    section_count: int
    chunk_count: int
    status: str
    created_at: str


class PaperListResponse(BaseModel):
    items: list[PaperListItem]
    total: int
    page: int
    page_size: int


class PaperDetailResponse(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    source_url: str | None
    status: str
    created_at: str
    sections: list[SectionInfo]
