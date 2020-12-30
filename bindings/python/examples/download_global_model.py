import json
import logging

import xaynet_sdk

LOG = logging.getLogger(__name__)


class Participant(xaynet_sdk.ParticipantABC):
    def __init__(self, model: list) -> None:
        self.model = model
        super().__init__()

    def deserialize_training_input(self, data: list) -> list:
        return data

    def train_round(self, training_input: list) -> list:
        pass

    def serialize_training_result(self, training_result: list) -> list:
        pass

    def participate_in_update_task(self) -> bool:
        return False

    def on_new_global_model(self, data: list) -> None:
        LOG.info("new global model")
        with open("global_model.bin", "w") as filehandle:
            filehandle.write(json.dumps(data))


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)8s %(message)s",
        level=logging.DEBUG,
        datefmt="%b %d %H:%M:%S",
    )

    participant = xaynet_sdk.spawn_participant(
        "http://127.0.0.1:8081", Participant, args=([0.1, 0.2, 0.345, 0.3],)
    )

    try:
        participant.join()
    except KeyboardInterrupt:
        participant.stop()


if __name__ == "__main__":
    main()
