# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Full-PDF page capture and scoped page-citation retrieval."""

# Surface PDF input errors with explicit messages at the document boundary.
# ruff: noqa: TRY003, TRY301

from __future__ import annotations

import hashlib
import io
import re
from urllib.parse import quote

from pydantic import BaseModel
from pypdf import PdfReader

from powercontext.builtin.artifacts.memory.models import MemoryCitation
from powercontext.builtin.runtime.models import SearchMemoryRequest
from powercontext.sources.definitions import AdapterSourceDefinition
from powercontext.sources.models import Source, SourceMaterialization
from powercontext.sources.projections import TEXT_EVIDENCE_PROJECTION_KEY, TextEvidence


class PDFDocumentInput(BaseModel):
    document_id: str
    content: bytes


class PDFPageInput(BaseModel):
    document_id: str
    document_sha256: str
    page_number: int
    text: str


class PDFPageSource(Source):
    document_id: str
    document_sha256: str
    page_number: int
    text: str


def parse_pdf_document(value: PDFDocumentInput) -> tuple[PDFPageInput, ...]:
    if not value.document_id.strip() or not value.content.startswith(b"%PDF-"):
        raise ValueError("invalid PDF document or document_id")
    digest = hashlib.sha256(value.content).hexdigest()
    try:
        reader = PdfReader(io.BytesIO(value.content), strict=False)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise ValueError("PDF requires a password")
        count = len(reader.pages)
        if count < 1:
            raise ValueError("PDF has no physical pages")
        return tuple(
            PDFPageInput(
                document_id=value.document_id,
                document_sha256=digest,
                page_number=index + 1,
                text=page.extract_text() or "",
            )
            for index, page in enumerate(reader.pages)
        )
    except Exception as exc:
        raise ValueError("PDF could not be fully parsed") from exc


def _source_name(value: PDFPageInput) -> str:
    document = quote(value.document_id, safe="")
    name = f"pdf:{document}:{value.document_sha256}:{value.page_number}"
    if len(name) > 256:
        document = hashlib.sha256(value.document_id.encode()).hexdigest()
        name = f"pdf:sha256-{document}:{value.document_sha256}:{value.page_number}"
    return name


class PDFPageAdapter:
    input_class = PDFPageInput
    name = "pdf-page"
    source_class = PDFPageSource

    async def resolve(self, value: PDFPageInput, /) -> PDFPageSource:
        return PDFPageSource(
            name=_source_name(value),
            materialization=SourceMaterialization.CAPTURED,
            **value.model_dump(),
        )

    async def read(self, source: PDFPageSource, /) -> PDFPageInput:
        return PDFPageInput.model_validate(source.model_dump(include=set(PDFPageInput.model_fields)))


class PDFTextProjection:
    name = TEXT_EVIDENCE_PROJECTION_KEY.name
    version = TEXT_EVIDENCE_PROJECTION_KEY.version
    source_class = PDFPageSource
    output_class = TextEvidence

    def project(self, source: PDFPageSource, /) -> TextEvidence:
        return TextEvidence(
            source_type="pdf-page",
            source_id=source.name,
            content=f"{source.document_id}\n{source.text}",
            metadata={
                "document_id": source.document_id,
                "document_sha256": source.document_sha256,
                "page_number": source.page_number,
            },
        )


PDF_PAGE_SOURCE_DEFINITION = AdapterSourceDefinition(PDFPageAdapter(), projections=(PDFTextProjection(),))


async def search_pdf_pages(memory, question: str, limit: int = 10) -> tuple[MemoryCitation, ...]:
    """Search persisted scoped Memory and return distinct exact page citations."""
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be positive")
    words = re.findall(r"[a-z]+|\d+", question.lower())
    stopwords = {
        "what",
        "which",
        "when",
        "where",
        "were",
        "was",
        "are",
        "the",
        "and",
        "for",
        "from",
        "how",
        "does",
        "did",
        "has",
        "have",
        "with",
        "its",
        "their",
        "that",
        "this",
        "of",
        "in",
        "to",
        "by",
        "a",
        "an",
        "is",
        "as",
        "on",
        "or",
        "at",
    }
    terms = list(dict.fromkeys(word for word in words if len(word) > 2 and word not in stopwords))
    queries = [question]
    if terms:
        queries.append(" ".join(terms))
        queries.extend(terms[: min(4, len(terms))])
    scores: dict[tuple[str, str], float] = {}
    hits_by_key = {}
    for query in dict.fromkeys(queries):
        page = await memory.search(SearchMemoryRequest(query=query, mode="fts", limit=max(limit * 3, 40)))
        for rank, hit in enumerate(page.hits, start=1):
            key = (hit.entry_id, hit.entry_version_id)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rank + 20)
            hits_by_key[key] = hit
    ordered = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
    return tuple(
        MemoryCitation(
            memory_ref=hits_by_key[key].memory_ref,
            entry_id=hits_by_key[key].entry_id,
            entry_version_id=hits_by_key[key].entry_version_id,
        )
        for key in ordered
    )


__all__ = ["PDF_PAGE_SOURCE_DEFINITION", "PDFDocumentInput", "PDFPageInput", "parse_pdf_document", "search_pdf_pages"]
