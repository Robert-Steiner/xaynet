import logging
import time

import xaynet_sdk

LOG = logging.getLogger(__name__)


def training():
    LOG.info("training")
    time.sleep(10.0)
    LOG.info("training done")


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
            participant.get_global_model()
            training()
            participant.set_local_model([1.2, 12.3, 4, 2])

    except KeyboardInterrupt:
        participant.stop()


if __name__ == "__main__":
    main()
