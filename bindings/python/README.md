![Xaynet banner](../../assets/xaynet_banner.png)

## Installation

**Prerequisites**

- Python (3.6 or higher)
- we also recommend using a virtual environment but this is optional

**Install it from source**

```
# first install rust via https://rustup.rs/
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# clone the xaynet repository
git clone https://github.com/xaynetwork/xaynet.git
cd xaynet/bindings/python

# install setuptools_rust
pip install setuptools_rust

# install xaynet-sdk
python setup.py install
```

## Participant API(s)

The Python SDK that consists of two experimental Xaynet participants 
`ParticipantABC` and `AsyncParticipant`.

**Nice to know:**

The Python participants do not implement a Xaynet participant from scratch. Under the hood
they use [`xaynet-mobile`](../../rust/xaynet-mobile/README.md) via
[`pyo3`](https://github.com/PyO3/pyo3).

### `ParticipantABC`

The `Participant` API is similar to the old one which we introduced in
[`v0.8.0`](https://github.com/xaynetwork/xaynet/blob/v0.8.0/python/sdk/xain_sdk/participant.py#L24).
The only difference is that the new participant now runs in it's own thread and provides additional
helpful methods.

**Public API of `ParticipantABC`  and `InternalParticipant`**

```python


class ParticipantABC(ABC):
    def train_round(self, training_input: Optional[TrainingInput]) -> TrainingResult:

    def serialize_training_result(self, training_result: TrainingResult) -> list:
        """
        Serializes the `training_result` into a `list`. The data type of the
        elements must match the data type defined in the coordinator configuration.

        Args:
            training_result: The `TrainingResult` of `train_round`.

        Returns:
            The `training_result` as a `list`.
        """

    def deserialize_training_input(self, global_model: list) -> TrainingInput:
        """
        Deserializes the global_model from a `list` to the type of `TrainingInput`.
        The data type of the elements matches the data type defined in the coordinator
        configuration. If no global model exists (usually in the first round), the method will
        not be called by the `InternalParticipant`.

        Args:
            global_model: The global model.

        Returns:
            The `TrainingInput` for `train_round`.
        """


    def participate_in_update_task(self) -> bool:
        """
        A callback used by the `InternalParticipant` to determine whether the
        `train_round` method should be called. This callback is only called
        if the participant is selected as a update participant. If `participate_in_update_task`
        returns the `False`, `train_round` will not be called by the `InternalParticipant`.

        Returns:
            Whether the `train_round` method should be called when the participant
            is an update participant.
        """


class InternalParticipant:
    def stop(self) -> List[int]:
        """
        Stops the execution of the participant and returns its serialized state.
        The serialized state can be passed to the `spawn_participant` function
        to restore a participant.

        Note:
            The serialized state contains unencrypted **private key(s)**. If used
            in production, it is important that the serialized state is securely saved.

        Returns:
            The serialized state of the participant.
        """
```

### `AsyncParticipant`

However, we have noticed that our `ParticipantABC` API may be difficult to integrate with existing
applications. Since the code for training the model has to be moved into the `train_round` method,
it can lead to significant changes in the existing codebase.

Therefore, we offer a second API in which the training of the model is no longer part of
the participant.

**Public API of `AsyncParticipant`**

```python
def spawn_async_participant(coordinator_url: str, state: Optional[List[int]]=None, scalar: float = 1.0)
    -> (AsyncParticipant, threading.Event):
    """
    Spawns a `AsyncParticipant` in a separate thread and returns a participant handle
    together with a global model notifier. If a `state` is passed, this state is restored, otherwise a
    new participant is created.

    Args:
        coordinator_url: The url of the coordinator.
        state: A serialized participant state. Defaults to `None`.
        scalar: The scalar used for masking. Defaults to `1.0`.

    Returns:
        A tuple which consists of an `AsyncParticipant` and a global model notifier.

    Raises:
        CryptoInit: If the initialization of the underling crypto library has failed.
        ParticipantInit: If the participant cannot be initialized. This is most
            likely caused by an invalid `coordinator_url`.
        ParticipantRestore: If the participant cannot be restored due to invalid
            serialized state. This exception can never be thrown if the`state` is `None`.
    """

class AsyncParticipant:
    def get_global_model(self) -> Optional[list]:
        """
        Fetches the current global model. This method can be called at any time. If no global
        model exists (usually in the first round), the method returns `None`.

        Returns:
            The current global model in the form of a list or `None`. The data type of the
            elements matches the data type defined in the coordinator configuration.

        Raises:
            GlobalModelUnavailable: If the participant cannot connect to the coordinator to get
                the global model.
            GlobalModelDataTypeMisMatch: If the data type of the global model does not match
                the data type defined in the coordinator configuration.
        """

    def set_local_model(self, local_model: list):
        """
        Sets a local model. This method can be called at any time. Internally the
        participant first caches the local model. As soon as the participant is selected as the
        update participant, the currently cached local model is used. This means that the cache
        is empty after this operation.

        If a local model is already in the cache and `set_local_model` is called with a new local
        model, the current cached local model will be replaced by the new one.
        If the participant is an update participant and there is no local model in the cache,
        the participant waits until a local model is set or until a new round has been started.

        Args:
            local_model: The local model in the form of a list. The data type of the
                elements must match the data type defined in the coordinator configuration.

        Raises:
            LocalModelLengthMisMatch: If the length of the local model does not match the
                length defined in the coordinator configuration.
            LocalModelDataTypeMisMatch: If the data type of the local model does not match
                the data type defined in the coordinator configuration.
        """

    def stop(self) -> List[int]:
        """
        Stops the execution of the participant and returns its serialized state.
        The serialized state can be passed to the `spawn_async_participant` function
        to restore a participant.

        Note:
            The serialized state contains unencrypted **private key(s)**. If used
            in production, it is important that the serialized state is securely saved.

        Returns:
            The serialized state of the participant.
```

## Enable logging of `xaynet-mobile`

If you are interested in what `xaynet-mobile` is doing under the hood,
you can turn on the logging via the environment variable `XAYNET_CLIENT`.

For example:

`XAYNET_CLIENT=info python examples/participate_in_update.py`

## How can I ... ?

We have created a few [examples](./examples/README.md) that show the basic methods in action.
But if something is missing, not very clear or not working properly, please let us know
by opening an issue.

We are happy to help and open to ideas or feedback :)
