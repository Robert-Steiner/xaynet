import threading

from .participant import *
from .participant_async import *


def run_participant(
    coordinator_url: str,
    participant,
    args=(),
    kwargs={},
    state=None,
    scalar: float = 1.0,
):
    internal_participant = InternalParticipant(
        coordinator_url, participant, args, kwargs, state, scalar
    )
    # spawns the thread. `start` call the `run` method of `InternalParticipant`
    # https://docs.python.org/3.8/library/threading.html#threading.Thread.start
    # https://docs.python.org/3.8/library/threading.html#threading.Thread.run
    internal_participant.start()
    return internal_participant


def run_participant_async(coordinator_url: str, state=None, scalar: float = 1.0):
    notifier = threading.Event()
    async_participant = AsyncParticipant(coordinator_url, notifier, state, scalar)
    async_participant.start()
    return (async_participant, notifier)
