"""Small, local retrieval for FSSAI source documents.

This module intentionally uses no embeddings or vector database. It preserves
the source page for every chunk and ranks chunks with deterministic keyword
overlap, behind a replaceable retriever interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .models import RuleEvidence


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SECTION_PATTERN = re.compile(
    r"^(?:schedule\s+[ivxlcdm]+|\d+(?:\.\d+)*\.?\s+.+|[A-Z][A-Z\s,&/-]{4,})$",
    re.IGNORECASE,
)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "the", "this", "to", "with",
}


@dataclass(frozen=True)
class DocumentPage:
    """Text extracted from one source-document page."""

    document: str
    source: str
    page_number: int
    text: str


class FssaiRuleRetriever(Protocol):
    """Interface for retrieving rule evidence for one claim and label context."""

    def retrieve(self, claim: str, context: str, limit: int = 3) -> list[RuleEvidence]:
        """Return relevant source chunks, preserving their original metadata."""


def load_fssai_documents(directory: str | Path) -> list[DocumentPage]:
    """Extract text from locally supplied PDF files, one record per page."""

    root = Path(directory)
    if not root.exists():
        return []

    pages: list[DocumentPage] = []
    pdf_paths = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")
    for path in pdf_paths:
        try:
            reader = PdfReader(path)
        except (OSError, PdfReadError):
            continue
        title = reader.metadata.title if reader.metadata and reader.metadata.title else path.stem
        source = str(path.relative_to(root))
        for number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(
                    DocumentPage(
                        document=title,
                        source=source,
                        page_number=number,
                        text=text.strip(),
                    )
                )
    return pages


def chunk_document_pages(pages: list[DocumentPage], max_characters: int = 1_200) -> list[RuleEvidence]:
    """Split page text by paragraphs without crossing page boundaries."""

    if max_characters < 1:
        raise ValueError("max_characters must be positive.")

    chunks: list[RuleEvidence] = []
    for page in pages:
        section: str | None = None
        current_parts: list[str] = []
        current_length = 0
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", page.text) if part.strip()]
        for paragraph in paragraphs:
            first_line = paragraph.splitlines()[0].strip()
            next_section = first_line if _SECTION_PATTERN.match(first_line) else None
            if next_section and current_parts:
                chunks.append(_make_evidence(page, section, current_parts))
                current_parts = []
                current_length = 0
            if next_section:
                section = next_section
            if current_parts and current_length + len(paragraph) + 2 > max_characters:
                chunks.append(_make_evidence(page, section, current_parts))
                current_parts = []
                current_length = 0
            if len(paragraph) > max_characters:
                if current_parts:
                    chunks.append(_make_evidence(page, section, current_parts))
                    current_parts = []
                    current_length = 0
                for start in range(0, len(paragraph), max_characters):
                    chunks.append(_make_evidence(page, section, [paragraph[start : start + max_characters]]))
                continue
            current_parts.append(paragraph)
            current_length += len(paragraph) + 2
        if current_parts:
            chunks.append(_make_evidence(page, section, current_parts))
    return chunks


def _make_evidence(page: DocumentPage, section: str | None, parts: list[str]) -> RuleEvidence:
    return RuleEvidence(
        document=page.document,
        source=page.source,
        page_number=page.page_number,
        section=section,
        text="\n\n".join(parts),
    )


class LocalFssaiRetriever:
    """Deterministic keyword-overlap retriever for the local FSSAI corpus."""

    def __init__(self, evidence: list[RuleEvidence]):
        self.evidence = evidence

    @classmethod
    def from_directory(cls, directory: str | Path) -> "LocalFssaiRetriever":
        return cls(chunk_document_pages(load_fssai_documents(directory)))

    def retrieve(self, claim: str, context: str, limit: int = 3) -> list[RuleEvidence]:
        if limit < 1:
            return []
        query_tokens = _tokens(f"{claim} {context}")
        if not query_tokens:
            return []

        ranked: list[tuple[int, int, RuleEvidence]] = []
        claim_phrase = " ".join(_tokens(claim))
        for index, evidence in enumerate(self.evidence):
            text_tokens = _tokens(evidence.text)
            score = sum(text_tokens.count(token) for token in query_tokens)
            if claim_phrase and claim_phrase in " ".join(text_tokens):
                score += len(query_tokens)
            if score:
                ranked.append((score, -index, evidence))
        ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
        return [item[2] for item in ranked[:limit]]


def _tokens(value: str) -> list[str]:
    return [token for token in _TOKEN_PATTERN.findall(value.lower()) if token not in _STOP_WORDS]
