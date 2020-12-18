# `keras_house_prices` Example

1. Adjust the coordinator settings

Change the model size to `55117` in `configs/docker-dev.toml`.

```toml
[model]
length = 55117
```

2. Start the coordinator

```shell
# in the root of the repository
docker-compose -f docker/docker-compose.yml up --build
```

**All the commands in this section are run from the
`bindings/python/example/keras_house_prices` directory.**

3. Install the SDK and the example:

```shell
python ../../setup.py install
pip install -e .
```

4. Download the dataset from Kaggle:
   https://www.kaggle.com/c/house-prices-advanced-regression-techniques/data

5. Extract the data (into
   `python/client_examples/keras_house_prices/data/` here, but the
   location doesn't matter):

```shell
(cd ./data ; unzip house-prices-advanced-regression-techniques.zip)
```

6. Prepare the data:

```shell
split-data --data-directory data --number-of-participants 10
```

7.  Run one participant:

```shell
XAYNET_CLIENT=info run-participant --data-directory data --coordinator-url http://127.0.0.1:8081
```

8. Repeat the previous step to run more participants
