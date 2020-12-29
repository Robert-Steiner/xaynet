import json
import logging
import time

import xaynet_sdk

LOG = logging.getLogger(__name__)


class Participant(xaynet_sdk.ParticipantABC):
    def __init__(self, p_id: int, model: list) -> None:
        self.p_id = p_id
        self.model = model
        super().__init__()

    def deserialize_training_input(self, data: list) -> list:
        return data

    def train_round(self, training_input: list) -> list:
        LOG.info("participant %s: start training", self.p_id)
        time.sleep(5.0)
        LOG.info("participant %s: training done", self.p_id)
        return self.model

    def serialize_training_result(self, training_result: list) -> list:
        return training_result

    def participate_in_update_task(self) -> bool:
        return True

    def on_new_global_model(self, data: list) -> None:
        with open("global_model.bin", "w") as filehandle:
            filehandle.write(json.dumps(data))


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)8s %(message)s",
        level=logging.DEBUG,
        datefmt="%b %d %H:%M:%S",
    )

    participant = xaynet_sdk.spawn_participant(
        "http://127.0.0.1:8081",
        Participant,
        args=(
            1,
            [1, 2, 3.45, 3],
        ),
    )

    participant_2 = xaynet_sdk.spawn_participant(
        "http://127.0.0.1:8081",
        Participant,
        args=(
            2,
            [3, 4, 4.5, 1],
        ),
    )

    participant_3 = xaynet_sdk.spawn_participant(
        "http://127.0.0.1:8081",
        Participant,
        args=(
            3,
            [1.23, 1.567, 12.3, 4.6, 2.4],
        ),
    )

    try:
        participant.join()
        participant_2.join()
        participant_3.join()
    except KeyboardInterrupt:
        participant.stop()
        participant_2.stop()
        participant_3.stop()


if __name__ == "__main__":
    main()
