from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from os.path import abspath, dirname, exists, isdir, join
from typing import Any, Callable, Optional, TypeVar, Generic

from functools import partial

import json, traceback

class EventCtrl:

    def __init__(self) -> None:
        self.events = []
    def enqueue_event(self, event : 'Event'):
        self.events.append(event)

T = TypeVar("T")
class Event(Generic[T]):
    def __init__(self, *args) -> None:
        self._event_args = list(args)

    def can_easily_fufill(self) -> bool:
        return False
    def easily_fufill(self) -> T:
        raise ValueError()

    def are_deps_fufilled(self):
        return not any(isinstance(v, Event) for v in self._event_args)
    def get_unfufilled_deps(self):
        return [v for v in self._event_args if isinstance(v, Event)]

    def set_dep_result(self, dep : 'Event', result : Any):
        for i, v in enumerate(self._event_args):
            if isinstance(v, Event) and dep is v:
                self._event_args[i] = result
    
    def get_run_function(self):
        return partial(type(self)._run, *self._event_args)


    @classmethod
    def _run(cls, *args):
        ctrl = EventCtrl()
        ret = cls.run(ctrl, *args)
        return (ctrl.events, ret)
        


    @classmethod
    def run(cls, ctrl : EventCtrl, *args) -> T:
        raise NotImplemented


class FileCachedEvent(Event[T]):
    _file_path : str
    def __init__(self, file_path, *args) -> None:
        self._file_path = file_path
        if not exists(dirname(abspath(file_path))):
            raise ValueError("But at least create the dir for a file cached event")

        # Smuggle in file_path as args to the runner
        super().__init__(file_path, *args)

    def can_easily_fufill(self):
        return exists(self._file_path)

    def easily_fufill(self) -> T:
        with open(self._file_path, "r") as f:
            return json.load(f)

    @classmethod
    def _run(cls, *args):
        file_path, *args = args
        events, result = super()._run(*args)

        with open(file_path, "w") as f:
            json.dump(result, f)

        return (events, result)




class EventManager:
    _futures : list[Future]
    _running_events : set[int]

    _future_to_event : dict[int, Event]

    _event_results : dict[int, Any]
    _dep_to_parent : dict[int, Event]

    _original_event_on_return : dict[int, Callable[[Event, Any], None] | None]
    _executor : ThreadPoolExecutor

    def fill_event_deps(self, event : Event):
        for dep in event.get_unfufilled_deps():
            i = id(dep)
            r = self._event_results.get(i)
            if r is not None:
                event.set_dep_result(dep, r)

    def _on_dep_complete(self, event : Event, ret):
        i = id(event)

        assert i in self._dep_to_parent
        parent = self._dep_to_parent[i]

        parent.set_dep_result(event, ret)

        if parent.are_deps_fufilled():
            self.attempt_enqueue(parent, on_return=self._original_event_on_return[id(parent)])
            del self._original_event_on_return[id(parent)]



    def attempt_enqueue(self, event : Event, on_return : Callable[[Event, Any], None] | None = None):
        i = id(event)



        # No repeated tasks
        if i in self._event_results or i in self._running_events:
            return


        self.fill_event_deps(event)

        if event.can_easily_fufill():
            ret = event.easily_fufill()
            self._event_results[id(event)] = ret 
            print(self._dep_to_parent[id(event)])
            if on_return is not None:
                on_return(event, ret)
            return

        if not event.are_deps_fufilled():
            self._original_event_on_return[i] = on_return

            for dep in event.get_unfufilled_deps():
                self._dep_to_parent[id(dep)] = event
                self.attempt_enqueue(dep, on_return=self._on_dep_complete)
        else: 
            run = event.get_run_function()
                
            fut = self._executor.submit(run)

            self._running_events.add(i)
            self._futures.append(fut)

            def on_done(fut_:Future):
                if fut_.exception() is not None:
                    print("Error in event: ")
                    traceback.print_exception(fut.exception())
                    return
                new_events, res = fut_.result()
                for event2 in new_events:
                    self.attempt_enqueue(event2)

                self._running_events.remove(i)
                self._event_results[id(event)] = res

                if on_return is not None:
                    on_return(event, res)

                self._futures.remove(fut_)


            fut.add_done_callback(on_done)

            self._future_to_event[id(fut)] = event


    def __init__(self, max_workers: Optional[int] = None) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        self._futures = []
        self._running_events = set()
        
        self._future_to_event = {}

        self._event_results = {}
        self._dep_to_parent = {}

        self._original_event_on_return = {}

    def __enter__(self) -> 'EventManager':
        self._executor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self._drain()
        finally:
            self._executor.__exit__(exc_type, exc, tb)
    def _drain(self):
        while self._futures:
            for fut in as_completed(self._futures):
                break


