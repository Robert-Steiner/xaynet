from abc import ABC, abstractmethod
import sys
import threading
import time
from typing import Any, List, Optional, Tuple, TypeVar

from justbackoff import Backoff

from . import xaynet_sdk

xaynet_sdk.enable_logging()

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


class InternalParticipant(threading.Thread):
    def __init__(self, participant: ParticipantABC, coordinator_url: str):
        self.participant = participant
        self.exit_event = threading.Event()
        self.poll_period = Backoff(min_ms=100, max_ms=10000, factor=1.2, jitter=False)

        xaynet_sdk.init_crypto()
        self.xaynet_participant = xaynet_sdk.Participant(coordinator_url)

        super(InternalParticipant, self).__init__(daemon=True)

    def run(self):
        try:
            self._run()
        except Exception as err:  # pylint: disable=broad-except
            print(err)
            self.exit_event.set()

    def train(self):
        # FIXME download global model
        training_input = self.participant.deserialize_training_input([])
        result = self.participant.train(training_input)
        data = self.participant.serialize_training_result(result)
        self.xaynet_participant.set_model(data)

    def _run(self):
        while not self.exit_event.is_set():
            self.xaynet_participant.tick()
            if self.xaynet_participant.should_set_model():
                self.train()
            if self.xaynet_participant.made_progress():
                self.poll_period.reset()
                self.exit_event.wait(timeout=self.poll_period.duration())
            else:
                self.exit_event.wait(timeout=self.poll_period.duration())

    def stop(self) -> List[int]:
        self.exit_event.set()
        return self.xaynet_participant.save()
