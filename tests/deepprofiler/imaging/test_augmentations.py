import numpy as np
import pytest
import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
tf.enable_resource_variables()
tf.disable_v2_behavior()

import deepprofiler.imaging.augmentations

config = tf.ConfigProto(
    device_count = {'GPU': 0}
)


def test_augment():
    crop = tf.constant(
        np.random.uniform(0, 1, (128, 128, 3)).astype(np.float32)
    )
    augmented = deepprofiler.imaging.augmentations.augment(crop)
    with tf.Session(config=config) as sess:
        augmented = augmented.eval()
    assert augmented.shape == crop.shape


def test_augment_multiple():
    crops = tf.constant(
        np.random.uniform(0, 1, (10, 128, 128, 3)).astype(np.float32)
    )
    augmented = deepprofiler.imaging.augmentations.augment_multiple(crops)
    with tf.Session(config=config) as sess:
        augmented = augmented.eval()
    assert augmented.shape == crops.shape
