"""Chunking utilities."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Sequence

from context_cache.utils.ids import new_id

_SEGMENT_RE = re.compile(r"\n\s*\n", re.MULTILINE)
_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?", re.MULTILINE)


@dataclass(slots=True)
class Segment:
    text: str
    start: int
    end: int


def chunk_text(
    text: str,
    target_tokens: int = 200,
    max_tokens: int = 256,
    min_tokens: int = 80,
    overlap_tokens: int = 20,
) -> list[dict[str, Any]]:
    """Split text into structured chunks respecting token budgets."""
    if not text.strip():
        return []

    segments = list(_iter_segments(text))
    expanded_segments: list[Segment] = []
    for segment in segments:
        expanded_segments.extend(_shrink_segment(segment, max_tokens))

    chunks: list[dict[str, Any]] = []
    current: list[Segment] = []
    current_tokens = 0

    for segment in expanded_segments:
        seg_tokens = _count_tokens(segment.text)
        if not current:
            current.append(segment)
            current_tokens = seg_tokens
            continue

        if current_tokens + seg_tokens <= max_tokens:
            current.append(segment)
            current_tokens += seg_tokens
            continue

        if current_tokens < min_tokens:
            current.append(segment)
            current_tokens += seg_tokens
        else:
            chunks.append(_finalize_chunk(text, current))
            current = _apply_overlap(current, overlap_tokens)
            current.append(segment)
            current_tokens = sum(_count_tokens(seg.text) for seg in current)

    if current:
        chunks.append(_finalize_chunk(text, current))

    return chunks


def _iter_segments(text: str) -> Iterator[Segment]:
    last_index = 0
    for match in _SEGMENT_RE.finditer(text):
        start = last_index
        end = match.start()
        segment = _trim_segment(text, start, end)
        if segment:
            yield segment
        last_index = match.end()
    if last_index < len(text):
        segment = _trim_segment(text, last_index, len(text))
        if segment:
            yield segment


def _trim_segment(text: str, start: int, end: int) -> Segment | None:
    seg_start = start
    seg_end = end
    while seg_start < seg_end and text[seg_start].isspace():
        seg_start += 1
    while seg_end > seg_start and text[seg_end - 1].isspace():
        seg_end -= 1
    if seg_start >= seg_end:
        return None
    return Segment(text=text[seg_start:seg_end], start=seg_start, end=seg_end)


def _shrink_segment(segment: Segment, max_tokens: int) -> list[Segment]:
    token_length = _count_tokens(segment.text)
    if token_length <= max_tokens:
        return [segment]
    sentences = list(_sentence_segments(segment))
    if sentences:
        shrunk: list[Segment] = []
        for sentence in sentences:
            shrunk.extend(_shrink_segment(sentence, max_tokens))
        if shrunk:
            return shrunk
    return _split_segment(segment, max_tokens)


def _sentence_segments(segment: Segment) -> Iterator[Segment]:
    for match in _SENTENCE_RE.finditer(segment.text):
        sentence = match.group().strip()
        if not sentence:
            continue
        rel_start, rel_end = match.span()
        start = segment.start + rel_start + segment.text[rel_start:].find(sentence)
        end = start + len(sentence)
        yield Segment(text=sentence, start=start, end=end)


def _split_segment(segment: Segment, max_tokens: int) -> list[Segment]:
    length = len(segment.text)
    if length <= max_tokens * 4:
        midpoint = length // 2
        return [
            Segment(text=segment.text[:midpoint], start=segment.start, end=segment.start + midpoint),
            Segment(text=segment.text[midpoint:], start=segment.start + midpoint, end=segment.end),
        ]
    pieces = max(1, math.ceil(length / (max_tokens * 4)))
    step = max(1, length // pieces)
    segments: list[Segment] = []
    cursor = 0
    while cursor < length:
        next_cursor = segment.start + min(length, cursor + step)
        segments.append(
            Segment(
                text=segment.text[cursor : cursor + step],
                start=segment.start + cursor,
                end=segment.start + min(length, cursor + step),
            )
        )
        cursor += step
    return segments


def _finalize_chunk(text: str, segments: Sequence[Segment]) -> dict[str, Any]:
    start = segments[0].start
    end = segments[-1].end
    chunk_text = text[start:end]
    token_count = _count_tokens(chunk_text)
    return {
        "id": new_id("chk"),
        "text": chunk_text,
        "start_char": start,
        "end_char": end,
        "token_count": token_count,
        "meta": {"segment_count": len(segments)},
    }


def _apply_overlap(segments: Sequence[Segment], overlap_tokens: int) -> list[Segment]:
    if not segments or overlap_tokens <= 0:
        return []
    reversed_segments = list(reversed(segments))
    retained: list[Segment] = []
    token_budget = 0
    for segment in reversed_segments:
        segment_tokens = _count_tokens(segment.text)
        if token_budget + segment_tokens > overlap_tokens:
            break
        retained.append(segment)
        token_budget += segment_tokens
    return list(reversed(retained))


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))


def build_chunk_payloads(
    document_id: str,
    chunk_dicts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach document metadata to raw chunk dictionaries."""
    payloads = []
    for ordinal, chunk in enumerate(chunk_dicts):
        payload = {
            "id": chunk["id"],
            "document_id": document_id,
            "ordinal": ordinal,
            "start_char": chunk["start_char"],
            "end_char": chunk["end_char"],
            "text": chunk["text"],
            "token_count": chunk["token_count"],
            "meta_json": chunk.get("meta", {}),
        }
        payloads.append(payload)
    return payloads


__all__ = ["chunk_text", "build_chunk_payloads"]
