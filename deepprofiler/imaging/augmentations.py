import tensorflow.compat.v1 as tf
from tensorflow_addons import image
tf.disable_v2_behavior()
import numpy as np

#################################################
## CROPPING AND TRANSFORMATION OPERATIONS
#################################################

def augment(crop):
    with tf.variable_scope("augmentation"):

        # Horizontal flips
        augmented = tf.image.random_flip_left_right(crop)

        # 90 degree rotations
        #angle = tf.random_uniform([1], minval=0, maxval=4, dtype=tf.int32)
        #augmented = tf.image.rot90(augmented, angle[0])

        # 360 degree rotations
        angle = tf.random_uniform([1], minval=0.0, maxval=2*np.pi, dtype=tf.float32)
        augmented = image.rotate(augmented, angle[0], interpolation="BILINEAR")

        # Translations
        offsets = tf.random_uniform([2],
                minval=-int(crop.shape[0].value*0.2),
                maxval=int(crop.shape[0].value*0.2)
        )
        augmented = image.translate(augmented, translations=offsets)

        # Illumination changes
        illum_s = tf.random_uniform([1], minval=0.8, maxval=1.2, dtype=tf.float32)
        #illum_t = tf.random_uniform([1], minval=-0.2, maxval=0.2, dtype=tf.float32)
        augmented = augmented * illum_s
        #augmented = augmented + illum_t

    return augmented


def augment_multiple(crops, parallel=10):
    with tf.variable_scope("augmentation"):
        return tf.map_fn(augment, crops, parallel_iterations=parallel, dtype=tf.float32)

