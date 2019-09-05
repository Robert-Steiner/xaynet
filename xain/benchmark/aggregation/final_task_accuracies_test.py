import os

import pytest
from absl import flags

from xain.helpers import sha1, storage

from . import final_task_accuracies

FLAGS = flags.FLAGS


def test_read_task_values(monkeypatch):
    # Prepare
    json_data = {
        "task_name": "TaskClass_foo_bar",
        "dataset": "fashion-mnist-100p-noniid-05cpp",
        "acc": 0.42,
    }

    def mock_read_json(_: str):
        return json_data

    monkeypatch.setattr(storage, "read_json", mock_read_json)

    expected_data = ("TaskClass", "05cpp", 0.42)

    # Execute
    actual_data = final_task_accuracies.read_task_values("any.json")

    # Assert
    assert expected_data == actual_data


@pytest.mark.integration
def test_read_all_task_values(monkeypatch, group_name, results_dir):
    # Prepare
    other_group_name = "other_group"
    assert group_name != other_group_name  # just in case

    group_dir = os.path.join(results_dir, group_name)
    other_group_dir = os.path.join(results_dir, other_group_name)

    files = [
        f"{group_dir}/task_1/results.json",
        f"{group_dir}/task_2/results.json",
        f"{other_group_dir}/task_1/results.json",
        f"{other_group_dir}/task_2/results.json",
    ]

    for fname in files:
        dname = os.path.dirname(fname)
        os.makedirs(dname)
        with open(fname, "x") as f:
            f.write("content not relevant")
            f.close()

    expected_results = files[:2]

    def mock_read_task_values(fname):
        return fname

    monkeypatch.setattr(
        final_task_accuracies, "read_task_values", mock_read_task_values
    )

    # Execute
    actual_results = final_task_accuracies.read_all_task_values(group_dir)

    # Assert
    assert set(actual_results) == set(expected_results)


@pytest.mark.integration
def test_plot_final_task_accuracies(output_dir, group_name, monkeypatch):
    # Prepare
    data = [
        (
            "unitary",
            [0.96, 0.90, 0.81, 0.72, 0.63, 0.54, 0.45, 0.36, 0.27, 0.18, 0.09],
            range(1, 12, 1),
        ),
        (
            "federated",
            [0.92, 0.89, 0.87, 0.85, 0.83, 0.81, 0.80, 0.79, 0.78, 0.77, 0.77],
            range(1, 12, 1),
        ),
    ]
    fname = f"plot_{group_name}.png"
    expected_filepath = os.path.join(output_dir, fname)
    expected_sha1 = "4b9fb44d7d3f92889ada5d59bb74d21a34a5fdaa"

    xticks_locations = range(1, 12, 1)
    xticks_labels = [chr(i) for i in range(65, 77, 1)]  # A, B, ..., K

    def mock_prepare_comparison_data(_: str):
        return (data, (xticks_locations, xticks_labels))

    monkeypatch.setattr(
        final_task_accuracies, "prepare_comparison_data", mock_prepare_comparison_data
    )

    # Execute
    actual_filepath = final_task_accuracies.plot()

    # If any error occurs we will be able to look at the plot. If the the ploting
    # logic is changed the file under this path can be used to get the new hash
    # after evaluating the rendered plot
    print(actual_filepath)

    # Assert
    assert expected_filepath == actual_filepath
    assert expected_sha1 == sha1.checksum(actual_filepath), "Checksum not matching"