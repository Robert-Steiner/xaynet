from .participant import *
from .xaynet_sdk import *


def run_participant(
    coordinator_url: str, participant, args=(), kwargs={}, scalar: float = 1.0
):
    internal_participant = InternalParticipant(
        coordinator_url, participant, args, kwargs
    )
    # spawns the thread. `start` call the `run` method of `InternalParticipant`
    # https://docs.python.org/3.8/library/threading.html#threading.Thread.start
    # https://docs.python.org/3.8/library/threading.html#threading.Thread.run
    internal_participant.start()
    return internal_participant
