from abc import ABC, abstractmethod
import logging
import threading
from typing import List, Optional, TypeVar

from justbackoff import Backoff

from xaynet_sdk import xaynet_sdk

# rust participant logging
xaynet_sdk.init_logging()
# python participant logging
LOG = logging.getLogger("participant")

TrainingResult = TypeVar("TrainingResult")
TrainingInput = TypeVar("TrainingInput")


class ParticipantABC(ABC):
    @abstractmethod
    def train_round(self, training_input: Optional[TrainingInput]) -> TrainingResult:
        raise NotImplementedError()

    @abstractmethod
    def serialize_training_result(self, training_result: TrainingResult) -> list:
        raise NotImplementedError()

    @abstractmethod
    def deserialize_training_input(self, global_model: list) -> TrainingInput:
        raise NotImplementedError()

    # FIXME: make it possible in the participant state machine to skip a task
    # def participate_in_sum_task(self) -> bool:
    #     True

    def participate_in_update_task(self) -> bool:
        return True

    def on_new_global_model(self, global_model: TrainingInput) -> None:
        pass

    def on_stop(self) -> None:
        pass


class InternalParticipant(threading.Thread):
    def __init__(
        self,
        coordinator_url: str,
        participant,
        p_args,
        p_kwargs,
        state,
        scalar,
    ):
        # xaynet rust participant
        self._xaynet_participant = xaynet_sdk.Participant(
            coordinator_url, scalar, state
        )

        # https://github.com/python/cpython/blob/3.9/Lib/multiprocessing/process.py#L80
        # stores the Participant class with its args and kwargs
        # the participant is created in the `run` method to ensure that the participant/ ml
        # model is initialized on the participant thread otherwise the participant lives on the main
        # thread which can created issues with some of the ml frameworks.
        self._participant = participant
        self._p_args = tuple(p_args)
        self._p_kwargs = dict(p_kwargs)

        self._exit_event = threading.Event()
        self._poll_period = Backoff(min_ms=100, max_ms=10000, factor=1.2, jitter=False)

        # global model cache
        self._global_model = None

        self._tick_lock = threading.Lock()

        super().__init__(daemon=True)

    def run(self):
        self._participant = self._participant(*self._p_args, *self._p_kwargs)

        try:
            self._run()
        except Exception as err:  # pylint: disable=broad-except
            LOG.error("unrecoverable error: %s shut down participant", err)
            self._exit_event.set()

    def _fetch_global_model(self):
        LOG.debug("fetch global model")
        global_model = self._xaynet_participant.global_model()
        if global_model is not None:
            data = self._participant.deserialize_training_input(global_model)
            self._global_model = data

    def _train(self):
        LOG.debug("train model")
        data = self._participant.train_round(self._global_model)
        local_model = self._participant.serialize_training_result(data)
        try:
            self._xaynet_participant.set_model(local_model)
        except (
            xaynet_sdk.LocalModelLengthMisMatch,
            xaynet_sdk.LocalModelDataTypeMisMatch,
        ) as err:
            LOG.warning("failed to set local model: %s", err)

    def _run(self):
        while not self._exit_event.is_set():
            self._tick()

    def _tick(self):
        with self._tick_lock:
            self._xaynet_participant.tick()

            if self._xaynet_participant.new_global_model():
                self._fetch_global_model()
                self._participant.on_new_global_model(self._global_model)

            if (
                self._xaynet_participant.should_set_model()
                and self._participant.participate_in_update_task()
            ):
                self._train()

            made_progress = self._xaynet_participant.made_progress()

        if made_progress:
            self._poll_period.reset()
            self._exit_event.wait(timeout=self._poll_period.duration())
        else:
            self._exit_event.wait(timeout=self._poll_period.duration())

    def stop(self) -> List[int]:
        """
        Stops the execution of the participant and returns its serialized state.
        The serialized state can be passed to the `spawn_participant` function
        to restore a participant.

        Note:
            The serialized state contains unencrypted **private key(s)**. If used
            in production, it is important that the serialized state is securely saved.

        Returns:
            The serialized state of the participant.
        """
        LOG.debug("stopping participant")
        self._exit_event.set()
        with self._tick_lock:
            state = self._xaynet_participant.save()
            LOG.debug("participant stopped")
        self._participant.on_stop()
        return state


# FIXME: wait for participate_in_sum_task
# class Task(Enum):
#     NONE = 0
#     SUM = 1
#     UPDATE = 2
