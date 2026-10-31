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

"""Branch-aware Pi v3 session evidence and durable connector checkpointing."""

# Report the exact invalid archive or checkpoint condition to import callers.
# ruff: noqa: TRY003

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from pydantic import BaseModel, JsonValue

from powercontext.sources.connectors import ConnectorRunCompletion, ConnectorRunSession, ConnectorRunStatus
from powercontext.sources.definitions import AdapterSourceDefinition
from powercontext.sources.models import Source, SourceMaterialization
from powercontext.sources.projections import TEXT_EVIDENCE_PROJECTION_KEY, TextEvidence


class PiSessionInput(BaseModel):
    content: bytes
    leaf_id: str | None = None


class PiEventInput(BaseModel):
    session_id: str
    event_id: str
    parent_id: str | None
    event_type: str
    role: str
    content: str
    record: dict[str, JsonValue]


class PiEventSource(Source):
    session_id: str
    event_id: str
    parent_id: str | None
    event_type: str
    role: str
    content: str
    record: dict[str, JsonValue]


def _text_blocks(value: object) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for block in value:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif block.get("type") == "toolCall":
            name, call_id = block.get("name"), block.get("id")
            arguments = block.get("arguments", {})
            if isinstance(name, str) and isinstance(call_id, str):
                parts.append(
                    f"[tool_call {name} {call_id}] "
                    + json.dumps(arguments, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                )
    return "\n".join(parts)


def _visible(record: dict[str, JsonValue]) -> tuple[str, str] | None:
    event_type = record.get("type")
    if event_type in ("compaction", "branch_summary"):
        role = str(event_type)
        body = record.get("summary")
    elif event_type == "custom_message":
        role = "custom"
        body = _text_blocks(record.get("content"))
    elif event_type == "message":
        message = record.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            return None
        role = message["role"]
        if role == "bashExecution":
            command, output = message.get("command"), message.get("output")
            body = f"$ {command}\n{output}" if isinstance(command, str) and isinstance(output, str) else ""
        elif role == "toolResult":
            tool_name, call_id = message.get("toolName"), message.get("toolCallId")
            text = _text_blocks(message.get("content"))
            body = (
                f"[tool_result {tool_name} {call_id}] {text}"
                if isinstance(tool_name, str) and isinstance(call_id, str)
                else text
            )
        else:
            body = _text_blocks(message.get("content"))
    else:
        return None
    if not isinstance(body, str) or not body.strip():
        return None
    return role, f"{role}: {body}"


def _parse_archive(value: PiSessionInput) -> tuple[str, dict[str, dict[str, JsonValue]], tuple[PiEventInput, ...]]:  # noqa: C901 - Pi event graph validation
    try:
        lines = [json.loads(line) for line in value.content.decode("utf-8-sig").splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid Pi session JSONL") from exc
    if not lines or not isinstance(lines[0], dict):
        raise ValueError("missing Pi session header")
    header = lines[0]
    session_id = header.get("id")
    if (
        header.get("type") != "session"
        or type(header.get("version")) is not int
        or header["version"] != 3
        or not isinstance(session_id, str)
        or not session_id.strip()
    ):
        raise ValueError("invalid Pi v3 session header")
    by_id: dict[str, dict[str, JsonValue]] = {}
    last_id: str | None = None
    for record in lines[1:]:
        if not isinstance(record, dict):
            raise TypeError("Pi event must be an object")
        event_id, parent_id = record.get("id"), record.get("parentId")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in by_id:
            raise ValueError("missing or duplicate Pi event identity")
        if parent_id is not None and (not isinstance(parent_id, str) or parent_id not in by_id):
            raise ValueError("Pi parent must be an earlier event")
        by_id[event_id] = record
        last_id = event_id
    leaf = value.leaf_id if value.leaf_id is not None else last_id
    if leaf is None:
        return session_id, by_id, ()
    if leaf not in by_id:
        raise ValueError("Pi leaf does not exist")
    path: list[dict[str, JsonValue]] = []
    while leaf is not None:
        record = by_id[leaf]
        path.append(record)
        leaf = record["parentId"]
    events: list[PiEventInput] = []
    for record in reversed(path):
        visible = _visible(record)
        if visible is None:
            continue
        role, content = visible
        events.append(
            PiEventInput(
                session_id=session_id,
                event_id=record["id"],
                parent_id=record["parentId"],
                event_type=record["type"],
                role=role,
                content=content,
                record=record,
            )
        )
    return session_id, by_id, tuple(events)


def parse_pi_session(value: PiSessionInput) -> tuple[PiEventInput, ...]:
    return _parse_archive(value)[2]


def _source_name(session_id: str, event_id: str) -> str:
    name = f"pi:{quote(session_id, safe='')}:{quote(event_id, safe='')}"
    if len(name) <= 256:
        return name
    identity = json.dumps([session_id, event_id], ensure_ascii=False, separators=(",", ":"))
    return "pi:sha256:" + hashlib.sha256(identity.encode()).hexdigest()


class PiEventAdapter:
    input_class = PiEventInput
    name = "pi-event"
    source_class = PiEventSource

    async def resolve(self, value: PiEventInput, /) -> PiEventSource:
        return PiEventSource(
            name=_source_name(value.session_id, value.event_id),
            materialization=SourceMaterialization.CAPTURED,
            **value.model_dump(),
        )

    async def read(self, source: PiEventSource, /) -> PiEventInput:
        return PiEventInput.model_validate(source.model_dump(include=set(PiEventInput.model_fields)))


class PiTextProjection:
    name = TEXT_EVIDENCE_PROJECTION_KEY.name
    version = TEXT_EVIDENCE_PROJECTION_KEY.version
    source_class = PiEventSource
    output_class = TextEvidence

    def project(self, source: PiEventSource, /) -> TextEvidence:
        return TextEvidence(
            source_type="pi-event",
            source_id=source.name,
            content=source.content,
            metadata={
                "session_id": source.session_id,
                "event_id": source.event_id,
                "parent_id": source.parent_id,
                "event_type": source.event_type,
                "role": source.role,
            },
        )


PI_EVENT_SOURCE_DEFINITION = AdapterSourceDefinition(PiEventAdapter(), projections=(PiTextProjection(),))


class PiSessionConnector:
    name = "pi-session-history"
    version = "1"
    source_definitions = frozenset({"pi-event"})

    def __init__(self, path: str | Path, leaf_id: str | None = None) -> None:
        self.path = Path(path)
        self.leaf_id = leaf_id

    async def run(self, session: ConnectorRunSession, /) -> ConnectorRunCompletion:
        session_id, by_id, events = _parse_archive(PiSessionInput(content=self.path.read_bytes(), leaf_id=self.leaf_id))
        previous = session.checkpoint or {"session_id": session_id, "events": {}}
        if (
            not isinstance(previous, dict)
            or previous.get("session_id") != session_id
            or not isinstance(previous.get("events"), dict)
        ):
            raise ValueError("Pi session checkpoint does not match archive")
        imported = dict(previous["events"])

        def checksum(record: dict[str, JsonValue]) -> str:
            canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            return hashlib.sha256(canonical.encode()).hexdigest()

        for event_id, digest in imported.items():
            if event_id not in by_id or checksum(by_id[event_id]) != digest:
                raise ValueError("previously imported Pi event was changed")
        for event in events:
            if event.event_id in imported:
                continue
            await session.submit(_source_name(session_id, event.event_id), "pi-event", event)
            imported[event.event_id] = checksum(event.record)
        return ConnectorRunCompletion(
            status=ConnectorRunStatus.COMPLETE, checkpoint={"session_id": session_id, "events": imported}
        )


__all__ = ["PI_EVENT_SOURCE_DEFINITION", "PiEventInput", "PiSessionConnector", "PiSessionInput", "parse_pi_session"]
