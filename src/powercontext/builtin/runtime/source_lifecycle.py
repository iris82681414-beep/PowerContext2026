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

"""Durable evidence dependency graph and native Memory availability propagation."""

# Graph registration and event validation expose precise contract errors.
# ruff: noqa: TRY003

from __future__ import annotations

import asyncio
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, Text, and_, insert, select, update

from powercontext.artifacts import ArtifactRef
from powercontext.builtin.artifacts.memory.models import MemoryCitation
from powercontext.builtin.runtime.models import GetMemoryEntryRequest
from powercontext.sources.models import SourceRef


class SourceLifecycleError(ValueError):
    """Invalid evidence identity, dependency, event, or generation request."""


class SourceLifecycleEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    revision: int = Field(strict=True, gt=0)
    sequence: int = Field(strict=True, gt=0)
    available: bool = Field(strict=True)
    reason: str

    @field_validator("node_id", "reason")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("lifecycle text cannot be blank")
        return value


_METADATA = MetaData()
_NODES = Table(
    "pc_source_lifecycle_nodes",
    _METADATA,
    Column("scope_id", String(256), primary_key=True),
    Column("node_id", String(256), primary_key=True),
    Column("kind", String(16), nullable=False),
    Column("payload", Text, nullable=False),
    Column("available", Boolean, nullable=False),
    Column("sequence", Integer, nullable=False, default=0),
    Column("event", Text, nullable=True),
)


class SourceLifecycleApplication:
    def __init__(self, runtime, database) -> None:
        self._runtime = runtime
        self._database = database
        self._initialized = False
        self._initialize_lock = asyncio.Lock()

    def for_scope(self, scope_id: str) -> ScopedSourceLifecycle:
        return ScopedSourceLifecycle(self, scope_id)

    async def _initialize(self) -> None:
        if self._initialized:
            return
        async with self._initialize_lock:
            if not self._initialized:
                async with self._database.transaction() as connection:
                    await connection.run_sync(_METADATA.create_all)
                self._initialized = True


class ScopedSourceLifecycle:
    def __init__(self, app: SourceLifecycleApplication, scope_id: str) -> None:
        self._app = app
        self.scope_id = scope_id

    async def _nodes(self) -> dict[str, dict]:
        await self._app._initialize()
        async with self._app._database.connection() as connection:
            rows = (await connection.execute(select(_NODES).where(_NODES.c.scope_id == self.scope_id))).mappings().all()
        return {
            str(row["node_id"]): {
                "kind": row["kind"],
                **json.loads(row["payload"]),
                "available": bool(row["available"]),
                "sequence": int(row["sequence"]),
                "event": None if row["event"] is None else json.loads(row["event"]),
            }
            for row in rows
        }

    async def _register(
        self, node_id: str, kind: str, reference, parents: tuple[str, ...], policy: str, revision: int = 1
    ) -> None:
        if not isinstance(node_id, str) or not node_id.strip() or len(node_id) > 256:
            raise SourceLifecycleError("invalid node identity")
        nodes = await self._nodes()
        if kind != "source":
            if (
                not parents
                or len(set(parents)) != len(parents)
                or node_id in parents
                or any(parent not in nodes for parent in parents)
            ):
                raise SourceLifecycleError("invalid lifecycle parents")
            if policy not in {"all", "any"}:
                raise SourceLifecycleError("invalid lifecycle policy")
        payload = {
            "reference": reference.model_dump(mode="json"),
            "parents": list(parents),
            "policy": policy,
            "revision": revision,
        }
        existing = nodes.get(node_id)
        if existing is not None:
            if existing["kind"] != kind or any(existing[key] != value for key, value in payload.items()):
                raise SourceLifecycleError("lifecycle node is already bound differently")
            return
        if kind == "source":
            await self._app._runtime.records.for_scope(self.scope_id).get_source(
                reference.source_type, reference.source_id
            )
        elif kind == "memory":
            await self._app._runtime.memory.for_scope(self.scope_id).get(GetMemoryEntryRequest(citation=reference))
        else:
            await self._app._runtime.records.for_scope(self.scope_id).get_artifact_revision(
                "topic-memory", reference.artifact_id, reference.revision
            )
        active = True if kind == "source" else self._supported(nodes, parents, policy)
        if kind == "memory" and not active:
            await self._set_memory(reference, False)
        async with self._app._database.transaction() as connection:
            await connection.execute(
                insert(_NODES).values(
                    scope_id=self.scope_id,
                    node_id=node_id,
                    kind=kind,
                    payload=json.dumps(payload, separators=(",", ":")),
                    available=active,
                    sequence=0,
                )
            )

    @staticmethod
    def _supported(nodes: dict[str, dict], parents: tuple[str, ...], policy: str) -> bool:
        statuses = (nodes[parent]["available"] for parent in parents)
        return all(statuses) if policy == "all" else any(statuses)

    async def register_source(self, node_id: str, source_ref: SourceRef, *, revision: int) -> None:
        if type(revision) is not int or revision < 1:
            raise SourceLifecycleError("invalid lifecycle revision")
        await self._register(node_id, "source", source_ref, (), "all", revision)

    async def register_memory(
        self, node_id: str, citation: MemoryCitation, *, parents: tuple[str, ...], policy: Literal["all", "any"]
    ) -> None:
        await self._register(node_id, "memory", citation, parents, policy)

    async def register_topic(
        self, node_id: str, artifact_ref: ArtifactRef, *, parents: tuple[str, ...], policy: Literal["all", "any"]
    ) -> None:
        if artifact_ref.family != "topic-memory":
            raise SourceLifecycleError("expected Topic Memory artifact")
        await self._register(node_id, "topic", artifact_ref, parents, policy)

    async def _set_memory(self, citation: MemoryCitation, available: bool) -> None:
        """Skip already-correct state so retries never create duplicate revisions."""
        runtime = self._app._runtime
        async with runtime._context(self.scope_id) as context, runtime._locked(self.scope_id):
            service = context.artifacts.memory
            current = await service.head(context.artifacts.memory_artifact_id)
            entry = next((item for item in await service.entries(current) if item.entry_id == citation.entry_id), None)
            if entry is None:
                raise SourceLifecycleError("Memory entry no longer exists")
            state = next(item.state for item in current.content.manifest.entries if item.entry_id == entry.entry_id)
            if (state == "active") == available:
                return
            if available:
                await service.reactivate(current, entries=(entry,))
            else:
                await service.forget(current, entries=(entry,))

    async def apply(self, event: SourceLifecycleEvent) -> list[str]:  # noqa: C901 - event reconciliation and propagation
        nodes = await self._nodes()
        root = nodes.get(event.node_id)
        if root is None or root["kind"] != "source" or event.revision != root["revision"]:
            raise SourceLifecycleError("unknown lifecycle source or revision")
        previous = root["sequence"]
        payload = event.model_dump(mode="json")
        if event.sequence < previous or (event.sequence == previous and root["event"] != payload):
            raise SourceLifecycleError("stale or conflicting lifecycle event")
        if event.sequence == previous:
            return sorted(node_id for node_id, node in nodes.items() if node["available"])
        root["available"] = event.available
        root["sequence"] = event.sequence
        root["event"] = payload
        resolved: dict[str, bool] = {}

        def available(node_id: str) -> bool:
            if node_id in resolved:
                return resolved[node_id]
            node = nodes[node_id]
            if node["kind"] == "source":
                result = node["available"]
            else:
                support = (available(parent) for parent in node["parents"])
                result = all(support) if node["policy"] == "all" else any(support)
            resolved[node_id] = result
            return result

        for node_id, node in nodes.items():
            node["available"] = available(node_id)
        for node in nodes.values():
            if node["kind"] == "memory":
                await self._set_memory(MemoryCitation.model_validate(node["reference"]), node["available"])
        async with self._app._database.transaction() as connection:
            for node_id, node in nodes.items():
                await connection.execute(
                    update(_NODES)
                    .where(and_(_NODES.c.scope_id == self.scope_id, _NODES.c.node_id == node_id))
                    .values(
                        available=node["available"],
                        sequence=node["sequence"],
                        event=None if node["event"] is None else json.dumps(node["event"], separators=(",", ":")),
                    )
                )
        return sorted(node_id for node_id, node in nodes.items() if node["available"])

    async def resolve(self, node_id: str, *, purpose: Literal["generation", "audit"]):
        nodes = await self._nodes()
        node = nodes.get(node_id)
        if (
            node is None
            or purpose not in {"generation", "audit"}
            or (purpose == "generation" and not node["available"])
        ):
            raise SourceLifecycleError("lifecycle reference unavailable")
        cls = {"source": SourceRef, "memory": MemoryCitation, "topic": ArtifactRef}[node["kind"]]
        return cls.model_validate(node["reference"])

    async def unavailable_topics(self) -> set[tuple[str, int]]:
        nodes = await self._nodes()
        return {
            (node["reference"]["artifact_id"], node["reference"]["revision"])
            for node in nodes.values()
            if node["kind"] == "topic" and not node["available"]
        }


__all__ = ["SourceLifecycleError", "SourceLifecycleEvent"]
