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

"""Share pending embeddings across callers and cache completed vectors."""

# Keep precise public validation errors and normalize backend failures in one place.
# ruff: noqa: TRY003, TRY301

from __future__ import annotations

import asyncio
import math
from collections import OrderedDict
from typing import Any

from powercontext.builtin.inference.models import EmbeddingResult, EmbeddingVector, InferenceUsage


class CoalescingEmbeddingModel:
    def __init__(
        self,
        model: Any,
        *,
        max_batch_size: int = 64,
        coalesce_ms: float = 5.0,
        cache_size: int = 1024,
    ) -> None:
        if type(max_batch_size) is not int or max_batch_size < 1:
            raise ValueError("max_batch_size must be positive")
        if type(cache_size) is not int or cache_size < 0:
            raise ValueError("cache_size must be nonnegative")
        if (
            isinstance(coalesce_ms, bool)
            or not isinstance(coalesce_ms, (int, float))
            or not math.isfinite(coalesce_ms)
            or coalesce_ms < 0
        ):
            raise ValueError("coalesce_ms must be nonnegative")
        self._model = model
        self.profile = model.profile
        self._max_batch_size = max_batch_size
        self._coalesce_ms = coalesce_ms
        self._cache_size = cache_size
        self._cache: OrderedDict[str, EmbeddingVector] = OrderedDict()
        self._pending: dict[str, asyncio.Future[tuple[EmbeddingVector, object, InferenceUsage]]] = {}
        self._queue: list[str] = []
        self._dispatch_task: asyncio.Task[None] | None = None
        self._batch_tasks: set[asyncio.Task[None]] = set()

    async def embed(self, texts: tuple[str, ...]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=(), usage=InferenceUsage(requests=0))
        waiting: dict[str, asyncio.Future[tuple[EmbeddingVector, object, InferenceUsage]]] = {}
        cached: dict[str, EmbeddingVector] = {}
        for text in dict.fromkeys(texts):
            if text in self._cache:
                cached[text] = self._cache[text]
                self._cache.move_to_end(text)
            elif text in self._pending:
                waiting[text] = self._pending[text]
            else:
                future: asyncio.Future[tuple[EmbeddingVector, object, InferenceUsage]] = (
                    asyncio.get_running_loop().create_future()
                )
                self._pending[text] = future
                self._queue.append(text)
                waiting[text] = future
        if self._queue and (self._dispatch_task is None or self._dispatch_task.done()):
            self._dispatch_task = asyncio.create_task(self._dispatch())

        resolved = await asyncio.gather(*(asyncio.shield(future) for future in waiting.values()))
        values = dict(cached)
        batches: dict[object, InferenceUsage] = {}
        for text, (vector, batch, usage) in zip(waiting, resolved, strict=True):
            values[text] = vector
            batches[batch] = usage
        usages = tuple(batches.values())
        return EmbeddingResult(
            vectors=tuple(values[text] for text in texts),
            usage=InferenceUsage(
                requests=sum(usage.requests for usage in usages),
                input_tokens=sum(usage.input_tokens or 0 for usage in usages)
                if any(usage.input_tokens is not None for usage in usages)
                else None,
                output_tokens=sum(usage.output_tokens or 0 for usage in usages)
                if any(usage.output_tokens is not None for usage in usages)
                else None,
            ),
        )

    async def _dispatch(self) -> None:
        while True:
            await asyncio.sleep(self._coalesce_ms / 1000)
            if not self._queue:
                return
            queued, self._queue = self._queue, []
            for start in range(0, len(queued), self._max_batch_size):
                task = asyncio.create_task(self._run_batch(tuple(queued[start : start + self._max_batch_size])))
                self._batch_tasks.add(task)
                task.add_done_callback(self._batch_tasks.discard)

    async def _run_batch(self, texts: tuple[str, ...]) -> None:
        batch = object()
        try:
            result = await self._model.embed(texts)
            if len(result.vectors) != len(texts):
                raise ValueError("embedding model returned the wrong number of vectors")
        except Exception as exc:
            for text in texts:
                future = self._pending.pop(text)
                if not future.done():
                    future.set_exception(exc)
            return
        for text, vector in zip(texts, result.vectors, strict=True):
            if self._cache_size:
                self._cache[text] = vector
                self._cache.move_to_end(text)
                if len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
            future = self._pending.pop(text)
            if not future.done():
                future.set_result((vector, batch, result.usage))


__all__ = ["CoalescingEmbeddingModel"]
