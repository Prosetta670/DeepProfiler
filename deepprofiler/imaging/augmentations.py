import tensorflow as tf
import numpy as np

#################################################
## CROPPING AND TRANSFORMATION OPERATIONS
#################################################

def augment(crop):
    with tf.variable_scope("augmentation"):

        # Horizontal flips
        augmented = tf.image.random_flip_left_right(crop)

        # 90 degree rotations
        angle = tf.random_uniform([1], minval=0, maxval=4, dtype=tf.int32)
        augmented = tf.image.rot90(augmented, angle[0])

        # 5 degree inclinations
        angle = tf.random_normal([1], mean=0.0, stddev=0.03*np.pi, dtype=tf.float32)
        augmented = tf.contrib.image.rotate(augmented, angle[0], interpolation="BILINEAR")

        # Translations (3% movement in x and y)
        offsets = tf.random_normal([2],
                mean=0,
                stddev=int(crop.shape[0].value*0.03)
        )
        augmented = tf.contrib.image.translate(augmented, translations=offsets)

        # Illumination changes (10% changes in intensity)
        illum_s = tf.random_normal([1], mean=1.0, stddev=0.1, dtype=tf.float32)
        illum_t = tf.random_normal([1], mean=0.0, stddev=0.1, dtype=tf.float32)
        augmented = augmented * illum_s + illum_t

    return augmented


def augment_multiple(crops, parallel=10):
    with tf.variable_scope("augmentation"):
        return tf.map_fn(augment, crops, parallel_iterations=parallel, dtype=tf.float32)

