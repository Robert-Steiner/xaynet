import time

import xaynet_sdk


class Participant(xaynet_sdk.ParticipantABC):
    def __init__(self, model: list) -> None:
        self.model = model
        super(Participant, self).__init__()

    def deserialize_training_input(self, data: list) -> list:
        return self.model

    def train(self, training_input: list) -> list:
        return self.model

    def serialize_training_result(self, _result: list) -> list:
        return self.model

    def on_new_global_model(self, data: list) -> None:
        with open('global_model.bin', 'w') as filehandle:
            filehandle.write(data)


participant = xaynet_sdk.run_participant(
    Participant([1, 2, 3.45, 3]), "http://127.0.0.1:8081"
)

try:
    participant.join()
except KeyboardInterrupt:
    print(participant.stop())  # prints the serialized participant state
