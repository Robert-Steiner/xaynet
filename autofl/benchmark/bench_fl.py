import time
from typing import List, Optional, Tuple

from absl import app, logging

from autofl.datasets import load_splits

from . import report, run

FLH_C = 0.1  # Fraction of participants used in each round of training
FLH_E = 4  # Number of training episodes in each round
FLH_B = 32  # Batch size used by participants

ROUNDS = 50


def benchmark_ul_fl_FashionMNIST_100p_IID_balanced():
    fn_name = benchmark_ul_fl_FashionMNIST_100p_IID_balanced.__name__
    logging.info("Starting {}".format(fn_name))

    xy_parts, xy_val, xy_test = load_splits("fashion_mnist_100p_IID_balanced")
    _run_unitary_versus_federated(fn_name, xy_parts, xy_val, xy_test, C=FLH_C)


def benchmark_ul_fl_FashionMNIST_100p_non_IID():
    fn_name = benchmark_ul_fl_FashionMNIST_100p_non_IID.__name__
    logging.info("Starting {}".format(fn_name))

    xy_parts, xy_val, xy_test = load_splits("fashion_mnist_100p_non_IID")
    _run_unitary_versus_federated(fn_name, xy_parts, xy_val, xy_test, C=FLH_C)


def benchmark_ul_fl_FashionMNIST_10p_IID_balanced():
    fn_name = benchmark_ul_fl_FashionMNIST_10p_IID_balanced.__name__
    logging.info("Starting {}".format(fn_name))
    xy_splits, xy_val, xy_test = load_splits("fashion_mnist_10s_600")
    _run_unitary_versus_federated(fn_name, xy_splits, xy_val, xy_test, C=0.3)


def benchmark_ul_fl_FashionMNIST_10p_1000():
    fn_name = benchmark_ul_fl_FashionMNIST_10p_1000.__name__
    logging.info("Starting {}".format(fn_name))
    xy_splits, xy_val, xy_test = load_splits("fashion_mnist_10s_500_1k_bias")
    _run_unitary_versus_federated(fn_name, xy_splits, xy_val, xy_test, C=0.3)


def benchmark_ul_fl_FashionMNIST_10p_5400():
    fn_name = benchmark_ul_fl_FashionMNIST_10p_5400.__name__
    logging.info("Starting {}".format(fn_name))
    xy_splits, xy_val, xy_test = load_splits("fashion_mnist_10s_single_class")
    _run_unitary_versus_federated(fn_name, xy_splits, xy_val, xy_test, C=0.3)


def _run_unitary_versus_federated(name: str, xy_splits, xy_val, xy_test, C):
    start = time.time()

    # Train CNN on a single partition ("unitary learning")
    # TODO train n models on all partitions
    partition_id = 0
    logging.info("Run unitary training using partition {}".format(partition_id))
    ul_hist, ul_loss, ul_acc = run.unitary_training(
        xy_splits[partition_id],
        xy_val,
        xy_test,
        epochs=ROUNDS * FLH_E,
        batch_size=FLH_B,
    )

    # Train CNN using federated learning on all partitions
    logging.info("Run federated learning using all partitions")
    fl_hist, _, fl_loss, fl_acc = run.federated_training(
        xy_splits, xy_val, xy_test, ROUNDS, C=C, E=FLH_E, B=FLH_B
    )

    end = time.time()

    # Write results JSON
    results = {
        "name": name,
        "start": start,
        "end": end,
        "duration": end - start,
        "FLH_C": C,
        "FLH_E": FLH_E,
        "FLH_B": FLH_B,
        "ROUNDS": ROUNDS,
        "unitary_learning": {
            "loss": float(ul_loss),
            "acc": float(ul_acc),
            "hist": ul_hist,
        },
        "federated_learning": {
            "loss": float(fl_loss),
            "acc": float(fl_acc),
            "hist": fl_hist,
        },
    }
    report.write_json(results, fname="results.json")

    # Plot results
    # TODO include aggregated participant histories in plot
    plot_data: List[Tuple[str, List[float], Optional[List[int]]]] = [
        (
            "Unitary Learning",
            ul_hist["val_acc"],
            [i for i in range(1, len(ul_hist["val_acc"]) + 1, 1)],
        ),
        (
            "Federated Learning",
            fl_hist["val_acc"],
            [i for i in range(FLH_E, len(fl_hist["val_acc"]) * FLH_E + 1, FLH_E)],
        ),
    ]
    # FIXME use different filenames for different datasets
    report.plot_accs(plot_data, fname="plot.png")


def main(_):
    # benchmark_ul_fl_FashionMNIST_10p_IID_balanced()
    # benchmark_ul_fl_FashionMNIST_10p_1000()
    # benchmark_ul_fl_FashionMNIST_10p_5400()
    # benchmark_ul_fl_FashionMNIST_100p_IID_balanced()
    benchmark_ul_fl_FashionMNIST_100p_non_IID()


if __name__ == "__main__":
    app.run(main=main)
