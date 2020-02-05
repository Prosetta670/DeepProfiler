import pytest
import tensorflow
import deepprofiler.imaging.cropping
import deepprofiler.dataset.image_dataset
import deepprofiler.dataset.metadata
import deepprofiler.dataset.target
import plugins.models.autoencoder


@pytest.fixture(scope="function")
def generator():
    return deepprofiler.imaging.cropping.CropGenerator


@pytest.fixture(scope="function")
def val_generator():
    return deepprofiler.imaging.cropping.SingleImageCropGenerator


def test_define_model(config, dataset):
    autoencoder, encoder, decoder, optimizer, loss = plugins.models.autoencoder.define_model(config, dataset)
    assert isinstance(autoencoder, tensorflow.keras.Model)
    assert isinstance(encoder, tensorflow.keras.Model)
    assert isinstance(decoder, tensorflow.keras.Model)
    assert isinstance(optimizer, str) or isinstance(optimizer, tensorflow.keras.optimizers.Optimizer)
    assert isinstance(loss, str) or callable(loss)


def test_init(config, dataset, generator, val_generator):
    dpmodel = plugins.models.autoencoder.ModelClass(config, dataset, generator, val_generator)
    autoencoder, encoder, decoder, optimizer, loss = plugins.models.autoencoder.define_model(config, dataset)
    assert dpmodel.feature_model.__eq__(autoencoder)
    assert dpmodel.encoder.__eq__(encoder)
    assert dpmodel.decoder.__eq__(decoder)
    assert dpmodel.optimizer.__eq__(optimizer)
    assert dpmodel.loss.__eq__(loss)
