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

"""Portable, independently verifiable full and incremental context payloads."""

# Wire decoding reports the exact invalid field to callers.
# ruff: noqa: TRY003

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from typing import Any

_PACK_SCHEMA = "powercontext.context-pack.v1"
_DELTA_SCHEMA = "powercontext.context-pack-delta.v1"


class ContextPackError(ValueError):
    """Invalid context pack, delta, or wire representation."""


def _wire(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _encoded(items: tuple[bytes, ...]) -> list[str]:
    return [base64.b64encode(item).decode("ascii") for item in items]


def _decoded(value: object) -> tuple[bytes, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ContextPackError("items must be a Base64 string array")
    try:
        return tuple(base64.b64decode(item, validate=True) for item in value)
    except (ValueError, binascii.Error) as exc:
        raise ContextPackError("invalid Base64 item") from exc


def _parse(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (TypeError, UnicodeDecodeError, ValueError) as exc:
        raise ContextPackError("invalid context JSON") from exc
    if not isinstance(value, dict):
        raise ContextPackError("context wire value must be an object")
    return value


def _digest(items: tuple[bytes, ...]) -> str:
    unsigned = {"schema": _PACK_SCHEMA, "items": _encoded(items)}
    return "sha256:" + hashlib.sha256(_wire(unsigned)).hexdigest()


@dataclass(frozen=True, slots=True)
class ContextPack:
    items: tuple[bytes, ...]
    digest: str
    byte_count: int

    @classmethod
    def build(cls, items: tuple[bytes, ...]) -> ContextPack:
        if not isinstance(items, tuple) or any(not isinstance(item, bytes) for item in items):
            raise ContextPackError("items must be a bytes tuple")
        digest = _digest(items)
        payload = {"schema": _PACK_SCHEMA, "items": _encoded(items), "digest": digest, "byte_count": 0}
        count = len(_wire(payload))
        while True:
            payload["byte_count"] = count
            next_count = len(_wire(payload))
            if next_count == count:
                return cls(items=items, digest=digest, byte_count=count)
            count = next_count

    @classmethod
    def from_content(cls, content: str, *, chunk_bytes: int = 512) -> ContextPack:
        if type(chunk_bytes) is not int or chunk_bytes < 1:
            raise ContextPackError("chunk_bytes must be positive")
        if not isinstance(content, str):
            raise ContextPackError("content must be text")
        chunks: list[bytes] = []
        current = bytearray()
        for character in content:
            encoded = character.encode("utf-8")
            if len(encoded) > chunk_bytes:
                raise ContextPackError("chunk limit cannot fit one UTF-8 character")
            if len(current) + len(encoded) > chunk_bytes:
                chunks.append(bytes(current))
                current.clear()
            current.extend(encoded)
        if current:
            chunks.append(bytes(current))
        return cls.build(tuple(chunks))

    def to_bytes(self) -> bytes:
        return _wire({
            "schema": _PACK_SCHEMA,
            "items": _encoded(self.items),
            "digest": self.digest,
            "byte_count": self.byte_count,
        })

    @classmethod
    def from_bytes(cls, data: bytes) -> ContextPack:
        value = _parse(data)
        if set(value) != {"schema", "items", "digest", "byte_count"} or value["schema"] != _PACK_SCHEMA:
            raise ContextPackError("invalid context pack schema")
        items = _decoded(value["items"])
        built = cls.build(items)
        if (
            value["digest"] != built.digest
            or type(value["byte_count"]) is not int
            or value["byte_count"] != built.byte_count
        ):
            raise ContextPackError("context pack digest or size mismatch")
        return built


@dataclass(frozen=True, slots=True)
class ContextPackDelta:
    base_digest: str
    target_digest: str
    prefix_items: int
    appended: tuple[bytes, ...]

    @classmethod
    def between(cls, base: ContextPack, target: ContextPack) -> ContextPackDelta:
        prefix = 0
        for old, new in zip(base.items, target.items, strict=False):
            if old != new:
                break
            prefix += 1
        return cls(base.digest, target.digest, prefix, target.items[prefix:])

    @property
    def byte_count(self) -> int:
        return len(self.to_bytes())

    def to_bytes(self) -> bytes:
        return _wire({
            "schema": _DELTA_SCHEMA,
            "base_digest": self.base_digest,
            "target_digest": self.target_digest,
            "prefix_items": self.prefix_items,
            "appended": _encoded(self.appended),
        })

    @classmethod
    def from_bytes(cls, data: bytes) -> ContextPackDelta:
        value = _parse(data)
        if (
            set(value) != {"schema", "base_digest", "target_digest", "prefix_items", "appended"}
            or value["schema"] != _DELTA_SCHEMA
        ):
            raise ContextPackError("invalid context delta schema")
        if type(value["prefix_items"]) is not int or value["prefix_items"] < 0:
            raise ContextPackError("invalid prefix length")
        for field in ("base_digest", "target_digest"):
            digest = value[field]
            if not isinstance(digest, str) or len(digest) != 71 or not digest.startswith("sha256:"):
                raise ContextPackError("invalid digest")
            try:
                int(digest[7:], 16)
            except ValueError as exc:
                raise ContextPackError("invalid digest") from exc
        return cls(value["base_digest"], value["target_digest"], value["prefix_items"], _decoded(value["appended"]))


def apply_context_pack_delta(base: ContextPack, delta: ContextPackDelta) -> ContextPack:
    if base.digest != delta.base_digest or ContextPack.build(base.items) != base:
        raise ContextPackError("delta base digest does not match")
    if type(delta.prefix_items) is not int or not 0 <= delta.prefix_items <= len(base.items):
        raise ContextPackError("delta prefix exceeds base")
    target = ContextPack.build((*base.items[: delta.prefix_items], *delta.appended))
    if target.digest != delta.target_digest:
        raise ContextPackError("delta target digest does not match")
    return target


__all__ = ["ContextPack", "ContextPackDelta", "ContextPackError", "apply_context_pack_delta"]
