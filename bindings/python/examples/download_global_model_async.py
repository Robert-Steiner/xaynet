import json
import logging

import xaynet_sdk

LOG = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)8s %(message)s",
        level=logging.DEBUG,
        datefmt="%b %d %H:%M:%S",
    )

    (participant, notifier) = xaynet_sdk.run_participant_async("http://127.0.0.1:8081")

    try:
        while 1:
            notifier.wait()
            LOG.info("new global model")
            global_model = participant.get_global_model()
            with open("global_model.bin", "w") as filehandle:
                filehandle.write(json.dumps(global_model))

    except KeyboardInterrupt:
        participant.stop()


if __name__ == "__main__":
    main()
