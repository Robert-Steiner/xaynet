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

    try:
        with open("state.bin", "r") as filehandle:
            restored_state = json.loads(filehandle.read())
    except IOError:
        LOG.info("no saved state availabe. initialize new participant")
        restored_state = None

    (participant, _) = xaynet_sdk.run_participant_async(
        "http://127.0.0.1:8081", restored_state
    )

    state = participant.stop()
    with open("state.bin", "w") as filehandle:
        filehandle.write(json.dumps(state))


if __name__ == "__main__":
    main()
