import logging
import threading

from justbackoff import Backoff

from . import xaynet_sdk

# rust participant logging
xaynet_sdk.init_logging()
# python participant logging
LOG = logging.getLogger("participant")


class AsyncParticipant(threading.Thread):
    def __init__(
        self,
        coordinator_url: str,
        notifier,
        state,
        scalar,
    ):
        # xaynet rust participant
        self._xaynet_participant = xaynet_sdk.Participant(
            coordinator_url, scalar, state
        )

        self._exit_event = threading.Event()
        self._poll_period = Backoff(min_ms=100, max_ms=10000, factor=1.2, jitter=False)

        # new global model notifier
        self._notifier = notifier

        # calls to an external lib are thread-safe https://stackoverflow.com/a/42023362
        # however, if a user calls `stop` in the middle of the `_tick` call, the
        # `save` method will be executed (which consumes the participant) and every following call
        # will fail with a call on an uninitialized participant. Therefore we lock during `tick`.
        self._tick_lock = threading.Lock()

        super(AsyncParticipant, self).__init__(daemon=True)

    def run(self):
        try:
            self._run()
        except Exception as err:  # pylint: disable=broad-except
            LOG.error("unrecoverable error: %s shut down participant", err)
            self._exit_event.set()

    def _notify(self):
        if self._notifier.is_set() is False:
            LOG.debug("notify that a new global model is available")
            self._notifier.set()

    def _run(self):
        while not self._exit_event.is_set():
            self._tick()

    def _tick(self):
        with self._tick_lock:
            self._xaynet_participant.tick()
            new_global_model = self._xaynet_participant.new_global_model()
            made_progress = self._xaynet_participant.made_progress()

        if new_global_model:
            self._notify()

        if made_progress:
            self._poll_period.reset()
            self._exit_event.wait(timeout=self._poll_period.duration())
        else:
            self._exit_event.wait(timeout=self._poll_period.duration())

    def get_global_model(self):
        LOG.debug("get global model")
        self._notifier.clear()
        with self._tick_lock:
            return self._xaynet_participant.global_model()

    def set_local_model(self, local_model):
        LOG.debug("set local model in model store")
        with self._tick_lock:
            self._xaynet_participant.set_model(local_model)

    def stop(self) -> list:
        LOG.debug("stop participant")
        self._exit_event.set()
        self._notifier.clear()
        with self._tick_lock:
            return self._xaynet_participant.save()
