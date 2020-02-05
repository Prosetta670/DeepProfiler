import importlib

import tensorflow.keras as keras
import deepprofiler.learning.profiling
import deepprofiler.dataset.image_dataset
import deepprofiler.dataset.metadata
import deepprofiler.dataset.target
import pytest
import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
tf.enable_resource_variables()
tf.disable_v2_behavior()
import os
import numpy as np


@pytest.fixture(scope="function")
def checkpoint(config, dataset):
    crop_generator = importlib.import_module(
        "plugins.crop_generators.{}".format(config["train"]["model"]["crop_generator"])) \
        .GeneratorClass
    profile_crop_generator = importlib.import_module(
        "plugins.crop_generators.{}".format(config["train"]["model"]["crop_generator"])) \
        .SingleImageGeneratorClass
    dpmodel = importlib.import_module("plugins.models.{}".format(config["train"]["model"]["name"])) \
        .ModelClass(config, dataset, crop_generator, profile_crop_generator)
    dpmodel.feature_model.compile(dpmodel.optimizer, dpmodel.loss)
    filename = os.path.join(config["paths"]["checkpoints"], config["profile"]["checkpoint"])
    dpmodel.feature_model.save_weights(filename)
    return filename


@pytest.fixture(scope="function")
def profile(config, dataset):
    return deepprofiler.learning.profiling.Profile(config, dataset)


def test_init(config, dataset, locations):
    metadata = deepprofiler.dataset.image_dataset.read_dataset(config)
    prof = deepprofiler.learning.profiling.Profile(config, metadata)
    test_num_channels = len(config["dataset"]["images"]["channels"])
    assert prof.config == config
    assert prof.dset.config == dataset.config
    assert prof.num_channels == test_num_channels
    assert prof.crop_generator == importlib.import_module(
        "plugins.crop_generators.{}".format(config["train"]["model"]["crop_generator"])).GeneratorClass
    assert isinstance(prof.profile_crop_generator, importlib.import_module(
            "plugins.crop_generators.{}".format(config["train"]["model"]["crop_generator"])).SingleImageGeneratorClass)
    assert isinstance(prof.dpmodel, importlib.import_module("plugins.models.{}".format(config["train"]["model"]["name"])).ModelClass)


def test_configure(profile, checkpoint):
    profile.configure()
    assert isinstance(profile.feat_extractor, keras.Model)
    assert isinstance(profile.sess, tf.Session)


def test_check(profile, metadata):
    assert profile.check(metadata.data)  # TODO: test false positive


def test_extract_features(profile, metadata, locations, checkpoint):
    meta = metadata.data.iloc[0]
    image = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)
    profile.configure()
    profile.extract_features(None, image, meta)
    output_file = profile.config["paths"]["features"] + "/{}_{}_{}.npz"\
        .format(meta["Metadata_Plate"], meta["Metadata_Well"], meta["Metadata_Site"])
    assert os.path.isfile(output_file)


def test_profile(config, dataset, data, locations, checkpoint):
    deepprofiler.learning.profiling.profile(config, dataset)
    for index, row in dataset.meta.data.iterrows():
        output_file = config["paths"]["features"] + "/{}_{}_{}.npz" \
            .format(row["Metadata_Plate"], row["Metadata_Well"], row["Metadata_Site"])
        assert os.path.isfile(output_file)
