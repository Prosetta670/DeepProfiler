import pytest
import tensorflow
import deepprofiler.imaging.cropping
import deepprofiler.dataset.image_dataset
import deepprofiler.dataset.metadata
import deepprofiler.dataset.target
import plugins.models.resnet50


@pytest.fixture(scope="function")
def generator():
    return deepprofiler.imaging.cropping.CropGenerator


@pytest.fixture(scope="function")
def val_generator():
    return deepprofiler.imaging.cropping.SingleImageCropGenerator


def test_define_model(config, dataset):
    config["train"]["model"]["name"] = "resnet" 
    config["train"]["model"]["params"]["conv_blocks"] = 18
    model, optimizer, loss = plugins.models.resnet50.define_model(config, dataset)
    assert isinstance(model, tensorflow.keras.Model)
    assert isinstance(optimizer, str) or isinstance(optimizer, tensorflow.keras.optimizers.Optimizer)
    assert isinstance(loss, str) or callable(loss)


def test_init(config, dataset, generator, val_generator):
    config["train"]["model"]["name"] = "resnet" 
    config["train"]["model"]["params"]["conv_blocks"] = 18
    dpmodel = plugins.models.resnet50.ModelClass(config, dataset, generator, val_generator)
    model, optimizer, loss = plugins.models.resnet50.define_model(config, dataset)
    assert dpmodel.feature_model.__eq__(model)
    assert dpmodel.optimizer.__eq__(optimizer)
    assert dpmodel.loss.__eq__(loss)
