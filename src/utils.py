import tensorflow as tf
import pandas as pd
import os
import shutil

SEED = 1337
from typing import List, Tuple, Dict, Union


def copy_folder_structure(source_folder: str, destination_folder: str):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    for item in os.listdir(source_folder):
        source_item = os.path.join(source_folder, item)
        destination_item = os.path.join(destination_folder, item)

        if os.path.isdir(source_item):
            copy_folder_structure(source_item, destination_item)


def move_files_based_on_list(
    source_folder: str, destination_folder: str, file_list: List[str]
):
    for filename in file_list:
        filename = filename[:-1]
        source_file = os.path.join(source_folder, filename)
        destination_file = os.path.join(destination_folder, filename)

        if os.path.exists(source_file):
            shutil.move(source_file, destination_file)


def make_datasets(source_folder: str):
    destination_folder = "../data/test"
    copy_folder_structure(source_folder, destination_folder)
    with open("../data/train/testing_list.txt", "r") as f:
        testing_files = f.readlines()
    move_files_based_on_list(source_folder, destination_folder, testing_files)

    destination_folder = "../data/val"
    copy_folder_structure(source_folder, destination_folder)
    with open("../data/train/validation_list.txt", "r") as f:
        validation_files = f.readlines()
    move_files_based_on_list(source_folder, destination_folder, validation_files)


def get_datasets() -> Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset]:
    ds_train = tf.keras.utils.audio_dataset_from_directory(
        directory="../data/train/audio",
        batch_size=None,
        seed=SEED,
        output_sequence_length=16000,
    )
    ds_val = tf.keras.utils.audio_dataset_from_directory(
        directory="../data/val/",
        batch_size=None,
        seed=SEED,
        output_sequence_length=16000,
    )
    ds_test = tf.keras.utils.audio_dataset_from_directory(
        directory="../data/test/",
        batch_size=None,
        seed=SEED,
        output_sequence_length=16000,
    )
    return ds_train, ds_val, ds_test


def get_callbacks(path: str) -> List[tf.keras.callbacks.Callback]:
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", patience=4
    )
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        path, save_best_only=True, monitor="val_accuracy", mode="max"
    )
    return [early_stopping, checkpoint]


def eval_and_save(
    model_type: str,
    ds_test: tf.data.Dataset,
    config: Dict[str, Union[int, str, float]],
    history: Dict[str, List[float]],
    path: str,
) -> None:
    model = tf.keras.models.load_model("../models/" + path)
    loss, acc = model.evaluate(ds_test)

    history = pd.DataFrame(history.history)
    history.to_csv(f"../history/{path.split('.')[0]}.csv")

    with open("../results/results.csv", "a") as f:
        f.write(f"{model_type};{model.count_params()};{loss};{acc};{config};{path}\n")


def waveform_to_spectrograms(
    waveforms: tf.Tensor, frame_length: int = 255, frame_step: int = 128
) -> tf.Tensor:
    waveforms = tf.reshape(waveforms, [-1, 16000])
    spectrogram = tf.signal.stft(
        waveforms, frame_length=frame_length, frame_step=frame_step
    )
    spectrogram = tf.abs(spectrogram)
    return spectrogram


def waveform_to_log_mel_spectrogram(
    waveform: tf.Tensor,
    sample_rate: int = 16000,
    frame_length: int = 255,
    frame_step: int = 128,
    num_mel_bins: int = 129,
) -> tf.Tensor:

    waveform = tf.reshape(waveform, [-1, 16000])
    stft = tf.signal.stft(waveform, frame_length=frame_length, frame_step=frame_step)

    magnitude_spectrogram = tf.abs(stft)
    num_spectrogram_bins = magnitude_spectrogram.shape[-1]
    linear_to_mel_weight_matrix = tf.signal.linear_to_mel_weight_matrix(
        num_mel_bins,
        num_spectrogram_bins,
        sample_rate,
        lower_edge_hertz=20,
        upper_edge_hertz=8000,
    )
    mel_spectrogram = tf.matmul(
        tf.square(magnitude_spectrogram), linear_to_mel_weight_matrix
    )
    mel_spectrogram = tf.pow(mel_spectrogram, 0.5)

    log_mel_spectrogram = tf.math.log(mel_spectrogram + 1e-6)

    return log_mel_spectrogram
