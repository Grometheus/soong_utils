#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from os import makedirs
from os.path import abspath, dirname, exists, isdir, join
from time import sleep
from typing import Any, Optional, TypeVar, Generic

from src.android_repo_searcher import get_manifest_tags

T = TypeVar("T")


def sorted_manifest_tags() -> list[str]:
    return list(sorted(get_manifest_tags()))


@dataclass
class EventCtrl:
    emitted: list[Event[Any]] = field(default_factory=list)

    def emit(self, event: Event[Any]) -> None:
        self.emitted.append(event)

    def flush(self) -> list[Event[Any]]:
        out = self.emitted
        self.emitted = []
        return out


class Event(Generic[T]):
    args: list[Any]

    def __init__(self, *args: Any) -> None:
        self.args = list(args)

    def run(self, ctrl: EventCtrl, *args: Any) -> T:
        raise NotImplementedError

    def dependencies(self) -> list[tuple[int, Event[Any]]]:
        deps: list[tuple[int, Event[Any]]] = []
        for i, a in enumerate(self.args):
            if isinstance(a, Event):
                deps.append((i, a))
        return deps


class FileCachedEvent(Event[T]):
    path: str

    def __init__(self, path: str, *args: Any) -> None:
        super().__init__(*args)
        self.path = path

    def can_resolve(self) -> bool:
        return exists(self.path)

    def load(self) -> T:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, value: T) -> None:
        makedirs(dirname(abspath(self.path)), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)

    def compute(self, ctrl: EventCtrl, *args: Any) -> T:
        raise NotImplementedError

    def run(self, ctrl: EventCtrl, *args: Any) -> T:
        if self.can_resolve():
            return self.load()
        value = self.compute(ctrl, *args)
        self.save(value)
        return value


class CachedTest(FileCachedEvent[str]):
    def compute(self, ctrl: EventCtrl, *args: Any) -> str:
        sleep(5.0)
        print(args)
        return "foo bar"


class PrintEvent(Event[None]):
    def run(self, ctrl: EventCtrl, *args: Any) -> None:
        print( CachedTest(*args))


class AndroidVersionEvent(Event[None]):
    def run(self, ctrl: EventCtrl, root_dir: str, tag: str) -> None:
        tag_dir = join(root_dir, "versions", tag)
        makedirs(tag_dir, exist_ok=True)
        # Add more work here, and ctrl.emit(...) to enqueue follow-ups.


@dataclass
class _Scheduled:
    event: Event[Any]
    future: Future[tuple[Any, list[Event[Any]]]]


class EventManager:
    def __init__(self, max_workers: Optional[int] = None) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: set[Future[tuple[Any, list[Event[Any]]]]] = set()
        self._future_to_event: dict[
            Future[tuple[Any, list[Event[Any]]]], Event[Any]
        ] = {}
        self._children_to_parents: dict[
            Future[tuple[Any, list[Event[Any]]]], list[tuple[Event[Any], int]]
        ] = {}

    def __enter__(self) -> EventManager:
        self._executor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self._drain()
        finally:
            self._executor.__exit__(exc_type, exc, tb)

    def enqueue_event(self, event: Event[Any]) -> None:
        deps = event.dependencies()
        if not deps:
            self._schedule(event)
            return

        for idx, dep in deps:
            dep_future = self._ensure_scheduled(dep)
            if dep_future.done():
                # Resolve immediately for cached/instantly-done deps
                try:
                    result, emitted = dep_future.result()
                except Exception as e:
                    print(
                        f"Dependency {dep.__class__.__name__} failed: {e}"
                    )
                    continue
                event.args[idx] = result
                for e in emitted:
                    self.enqueue_event(e)
            else:
                self._children_to_parents.setdefault(dep_future, []).append(
                    (event, idx)
                )

        # If all deps resolved synchronously, schedule parent now.
        if not event.dependencies():
            self._schedule(event)

    def _ensure_scheduled(
        self, event: Event[Any]
    ) -> Future[tuple[Any, list[Event[Any]]]]:
        if isinstance(event, FileCachedEvent) and event.can_resolve():
            f: Future[tuple[Any, list[Event[Any]]]] = Future()
            f.set_result((event.load(), []))
            return f
        return self._schedule(event).future

    def _schedule(self, event: Event[Any]) -> _Scheduled:
        def _runner(ev: Event[Any]) -> tuple[Any, list[Event[Any]]]:
            ctrl = EventCtrl()
            result = ev.run(ctrl, *ev.args)
            return result, ctrl.flush()

        fut = self._executor.submit(_runner, event)
        self._futures.add(fut)
        self._future_to_event[fut] = event
        return _Scheduled(event=event, future=fut)

    def _maybe_schedule_parent(self, parent: Event[Any]) -> None:
        if parent.dependencies():
            return
        self._schedule(parent)

    def _drain(self) -> None:
        while self._futures:
            for fut in as_completed(list(self._futures)):
                self._futures.discard(fut)
                event = self._future_to_event.pop(fut, None)
                exc = fut.exception()
                if exc is not None:
                    print(f"Event {event.__class__.__name__} failed: {exc}")
                    continue

                result, emitted = fut.result()

                # Notify parents waiting on this child.
                for parent, idx in self._children_to_parents.pop(fut, []):
                    parent.args[idx] = result
                    self._maybe_schedule_parent(parent)

                # Enqueue any newly emitted events.
                for e in emitted:
                    self.enqueue_event(e)

                break


def output_to(out_dir: str) -> None:
    with EventManager(max_workers=32) as mng:
        # Demo: second run should still print because dependency resolves
        x = CachedTest(join(out_dir, "cacheme.json"))
        mng.enqueue_event(
            PrintEvent(x)
        )
        mng.enqueue_event(
            PrintEvent(x)
        )

        # Example for later:
        # tags = sorted_manifest_tags()
        # with open(join(out_dir, "manifest_tags.json"), "w", encoding="utf-8") as f:
        #     json.dump(tags, f, indent=2, ensure_ascii=False)
        # for tag in tags:
        #     mng.enqueue_event(AndroidVersionEvent(out_dir, tag))


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: collect_data.py OUTPUT_DIR")
        sys.exit(1)

    output = abspath(sys.argv[1])
    if not exists(output) or not isdir(output):
        print("Error: OUTPUT_DIR must be an existing directory")
        sys.exit(1)

    output_to(output)


if __name__ == "__main__":
    main()
