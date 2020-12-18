from abc import ABC, abstractmethod
import sys
import threading
import time
from typing import Any, List, Optional, Tuple, TypeVar

from justbackoff import Backoff

from . import xaynet_sdk

xaynet_sdk.init_logging()
xaynet_sdk.init_crypto()

TrainingResult = TypeVar("TrainingResult")
TrainingInput = TypeVar("TrainingInput")


class ParticipantABC(ABC):
    @abstractmethod
    def train(self, training_input: TrainingInput) -> TrainingResult:
        raise NotImplementedError()

    @abstractmethod
    def serialize_training_result(self, training_result: TrainingResult) -> list:
        raise NotImplementedError()

    @abstractmethod
    def deserialize_training_input(self, data: list) -> TrainingInput:
        raise NotImplementedError()

    @abstractmethod
    def on_new_global_model(self, data: list) -> None:
        raise NotImplementedError()


class InternalParticipant(threading.Thread):
    def __init__(
        self,
        coordinator_url: str,
        participant,
        p_args=(),
        p_kwargs={},
        scalar: float = 1.0,
    ):
        # https://github.com/python/cpython/blob/3.9/Lib/multiprocessing/process.py#L80
        print("__init__ip", threading.current_thread().name, threading.get_ident())
        # stores the Participant class with args
        # the participant is created in the run thread otherwise the participant lives on the main
        # thread which can created issues with some of the ml frameworks.
        self._participant = participant
        self._p_args = tuple(p_args)
        self._p_kwargs = dict(p_kwargs)

        # xaynet ffi participant
        self._xaynet_participant = xaynet_sdk.Participant(coordinator_url, scalar)

        self._exit_event = threading.Event()
        self._poll_period = Backoff(min_ms=100, max_ms=10000, factor=1.2, jitter=False)

        # global model cache
        self._global_model = None

        super(InternalParticipant, self).__init__(daemon=True)

    def run(self):
        self._participant = self._participant(*self._p_args, *self._p_kwargs)

        try:
            self._run()
        except Exception as err:  # pylint: disable=broad-except
            print(err)
            self._exit_event.set()

    def _fetch_global_model(self):
        global_model = self._xaynet_participant.global_model()
        if global_model != None:
            self._global_model = self._participant.deserialize_training_input(
                global_model
            )
            self._participant.on_new_global_model(self._global_model)

    def _train(self):
        result = self._participant.train(self._global_model)
        data = self._participant.serialize_training_result(result)
        self._xaynet_participant.set_model(data)

    def _run(self):
        while not self._exit_event.is_set():
            self._xaynet_participant.tick()
            if self._xaynet_participant.new_global_model():
                self._fetch_global_model()
            if self._xaynet_participant.should_set_model():
                self._train()
            if self._xaynet_participant.made_progress():
                self._poll_period.reset()
                self._exit_event.wait(timeout=self._poll_period.duration())
            else:
                self._exit_event.wait(timeout=self._poll_period.duration())

    def stop(self) -> List[int]:
        self._exit_event.set()
        return self._xaynet_participant.save()
