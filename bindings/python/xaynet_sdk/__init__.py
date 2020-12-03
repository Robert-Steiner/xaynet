from .participant import *
from .xaynet_sdk import *


def run_participant(participant: ParticipantABC, coordinator_url: str):
    internal_participant = InternalParticipant(participant, coordinator_url)
    # spawns the thread. `start` call the `run` method of `InternalParticipant`
    # https://docs.python.org/3.8/library/threading.html#threading.Thread.start
    # https://docs.python.org/3.8/library/threading.html#threading.Thread.run
    internal_participant.start()
    return internal_participant
