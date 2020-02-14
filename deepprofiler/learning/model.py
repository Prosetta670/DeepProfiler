import gc
import os
import random
import abc


import comet_ml
import tensorflow
import numpy as np
import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
tf.enable_resource_variables()
tf.disable_v2_behavior()

import deepprofiler.dataset.utils
import deepprofiler.imaging.cropping
import deepprofiler.learning.validation

##################################################
# This class should be used as an abstract base
# class for plugin models.
##################################################


class DeepProfilerModel(abc.ABC):

    def __init__(self, config, dset, crop_generator, val_crop_generator):
        self.feature_model = None
        self.loss = None
        self.optimizer = None
        self.config = config
        self.dset = dset
        self.train_crop_generator = crop_generator(config, dset)
        self.val_crop_generator = val_crop_generator(config, dset)
        self.random_seed = None
        if "comet_ml" not in config["train"].keys():
            self.config["train"]["comet_ml"]["track"] = False

    def seed(self, seed):
        self.random_seed = seed
        random.seed(seed)
        np.random.seed(seed)
        tf.set_random_seed(seed)

    def train(self, epoch=1, metrics=["accuracy"], verbose=1):
        # Raise ValueError if feature model isn't properly defined
        check_feature_model(self)
        # Print model summary
        if verbose != 0:
            self.feature_model.summary()
        # Compile model
        self.feature_model.compile(self.optimizer, self.loss, metrics)
        # Create comet ml experiment
        experiment = setup_comet_ml(self)
        # Create tf configuration
        configuration = tf_configure(self)
        # Start train crop generator
        crop_session = start_crop_session(self, configuration)
        # Start val crop generator
        val_session, x_validation, y_validation = start_val_session(self, configuration)
        # Create main session
        main_session = start_main_session(configuration)
        epochs, steps, lr_schedule_epochs, lr_schedule_lr = setup_params(self, experiment)
        if verbose != 0:  # verbose is only 0 when optimizing hyperparameters
            # Load weights
            load_weights(self, epoch)
            # Create callbacks
            callbacks = setup_callbacks(self, lr_schedule_epochs, lr_schedule_lr, self.dset, experiment)
        else:
            callbacks = None
        # Create params (epochs, steps, log model params to comet ml)

        #tf.compat.v1.keras.backend.get_session().run(tf.initialize_all_variables())
        # Train model
        self.feature_model.fit_generator(
            generator=self.train_crop_generator.generate(crop_session),
            steps_per_epoch=steps,
            epochs=epochs,
            callbacks=callbacks,
            verbose=verbose,
            initial_epoch=epoch - 1,
            validation_data=(x_validation, y_validation)
        ) 
            
        # Stop threads and close sessions
        close(self, crop_session)
        # Return the feature model and validation data
        return self.feature_model, x_validation, y_validation


def check_feature_model(dpmodel):
    if "feature_model" not in vars(dpmodel) or not isinstance(dpmodel.feature_model, tensorflow.keras.Model):
        raise ValueError("Feature model is not properly defined.")


def setup_comet_ml(dpmodel):
    if dpmodel.config["train"]["comet_ml"]["track"]:
        experiment = comet_ml.Experiment(
            api_key=dpmodel.config["train"]["comet_ml"]["api_key"],
            project_name=dpmodel.config["train"]["comet_ml"]["project_name"]
        )
        if dpmodel.config["experiment_name"] != "results":
            experiment.set_name(dpmodel.config["experiment_name"])
        experiment.log_others(dpmodel.config)
    else:
        experiment = None
    return experiment


def start_crop_session(dpmodel, configuration):
    crop_graph = tf.Graph()
    with crop_graph.as_default():
#         cpu_config = tf.ConfigProto(device_count={"CPU": 1, "GPU": 0})
#         cpu_config.gpu_options.visible_device_list = ""
        crop_session = tf.Session(config=configuration)
        dpmodel.train_crop_generator.start(crop_session)
    gc.collect()
    return crop_session


def tf_configure(dpmodel):
    configuration = tf.ConfigProto()
    configuration.gpu_options.allow_growth = True
    return configuration


def start_val_session(dpmodel, configuration):
    crop_graph = tf.Graph()
    with crop_graph.as_default():
        val_session = tf.Session(config=configuration)
        tf.compat.v1.keras.backend.set_session(val_session)
        dpmodel.val_crop_generator.start(val_session)
        x_validation, y_validation = deepprofiler.learning.validation.load_validation_data(
            dpmodel.config,
            dpmodel.dset,
            dpmodel.val_crop_generator,
            val_session)
    gc.collect()
    return val_session, x_validation, y_validation


def start_main_session(configuration):
    main_session = tf.Session(config=configuration)
    tf.compat.v1.keras.backend.set_session(main_session)
    return main_session


def load_weights(dpmodel, epoch):
    output_file = dpmodel.config["paths"]["checkpoints"] + "/checkpoint_{epoch:04d}.hdf5"
    previous_model = output_file.format(epoch=epoch - 1)
    if epoch >= 1 and os.path.isfile(previous_model):
        dpmodel.feature_model.load_weights(previous_model)
        print("Weights from previous model loaded:", previous_model)
    else:
        # Initialize all tf variables to avoid tf bug
        tf.compat.v1.keras.backend.get_session().run(tf.global_variables_initializer())


def setup_callbacks(dpmodel, lr_schedule_epochs, lr_schedule_lr, dset, experiment):
    # Checkpoints
    output_file = dpmodel.config["paths"]["checkpoints"] + "/checkpoint_{epoch:04d}.hdf5"
    callback_model_checkpoint = tensorflow.keras.callbacks.ModelCheckpoint(
        filepath=output_file,
        save_weights_only=True,
        save_best_only=False
    )
    
    # CSV Log
    csv_output = dpmodel.config["paths"]["logs"] + "/log.csv"
    callback_csv = tensorflow.keras.callbacks.CSVLogger(filename=csv_output)

    # Queue stats
    qstats = tensorflow.keras.callbacks.LambdaCallback(
        on_train_begin=lambda logs: dset.show_setup(),
        on_epoch_end=lambda epoch, logs: experiment.log_metrics(dset.show_stats()) if experiment else dset.show_stats()
    )

    # Learning rate schedule
    def lr_schedule(epoch, lr):
        if epoch in lr_schedule_epochs:
            return lr_schedule_lr[lr_schedule_epochs.index(epoch)]
        else:
            return lr

    # Collect all callbacks
    if lr_schedule_epochs:
        callback_lr_schedule = tensorflow.keras.callbacks.LearningRateScheduler(lr_schedule, verbose=1)
        callbacks = [callback_model_checkpoint, callback_csv, callback_lr_schedule, qstats]
    else:
        callbacks = [callback_model_checkpoint, callback_csv, qstats]
    return callbacks


def setup_params(dpmodel, experiment):
    epochs = dpmodel.config["train"]["model"]["epochs"]
    steps = dpmodel.dset.steps_per_epoch
    lr_schedule_epochs = []
    lr_schedule_lr = []
    if dpmodel.config["train"]["comet_ml"]["track"]:
        params = dpmodel.config["train"]["model"]["params"]
        experiment.log_others(params)
    if "lr_schedule" in dpmodel.config["train"]["model"]:
        if dpmodel.config["train"]["model"]["lr_schedule"] == "cosine":
            lr_schedule_epochs = [x for x in range(epochs)]
            init_lr = dpmodel.config["train"]["model"]["params"]["learning_rate"]
            # Linear warm up
            lr_schedule_lr = [init_lr/(5-t) for t in range(5)]
            # Cosine decay
            lr_schedule_lr += [0.5 * (1 + np.cos((np.pi * t) / epochs)) * init_lr for t in range(5, epochs)]
        else:
            assert len(dpmodel.config["train"]["model"]["lr_schedule"]["epoch"]) == \
                   len(dpmodel.config["train"]["model"]["lr_schedule"]["lr"]), "Make sure that the length of " \
                                                                               "lr_schedule->epoch equals the length of " \
                                                                               "lr_schedule->lr in the config file."

            lr_schedule_epochs = dpmodel.config["train"]["model"]["lr_schedule"]["epoch"]
            lr_schedule_lr = dpmodel.config["train"]["model"]["lr_schedule"]["lr"]

    return epochs, steps, lr_schedule_epochs, lr_schedule_lr


def close(dpmodel, crop_session):
    print("Complete! Closing session.", end=" ", flush=True)
    dpmodel.train_crop_generator.stop(crop_session)
    crop_session.close()
    print("All set.")
    gc.collect()
