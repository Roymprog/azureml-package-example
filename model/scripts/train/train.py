# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from azureml.core.run import Run
from azureml.core import Model, Dataset
from azureml.core.resource_configuration import ResourceConfiguration

from sklearn import __version__ as sklearnver
import pandas as pd
import numpy as np
import joblib
import click
import os

@click.command()
@click.option("--train_features_dataset", required=True)
@click.option("--train_labels_dataset", required=True)
@click.option("--model_output_dir", required=True)
def train(
    train_features_dataset,
    train_labels_dataset,
    model_output_dir,
):
    # Ensure output dir exists
    os.makedirs(model_output_dir, exist_ok=True)

    run = Run.get_context()
    ws = run.experiment.workspace
    datastore = ws.get_default_datastore()

    X_train = pd.read_csv(train_features_dataset)
    y_train = pd.read_csv(train_labels_dataset)

    # Register Dataset for reference wrt model
    X_ds = Dataset.Tabular.register_pandas_dataframe(X_train, target=datastore, name='diabetes_training_features')
    y_ds = Dataset.Tabular.register_pandas_dataframe(y_train, target=datastore, name='diabetes_training_labels')

    print(f"Train data preview: {X_train}")
    print(f"Train label preview: {y_train}")

    # list of numbers from 0.0 to 1.0 with a 0.05 interval
    alphas = np.arange(0.0, 1.0, 0.05)

    for alpha in alphas:
        # Use Ridge algorithm to create a regression model
        reg = Ridge(alpha=alpha)
        reg.fit(X_train, y_train)

        preds = reg.predict(X_train)
        mse = mean_squared_error(preds, y_train)

        run.parent.log('alpha', alpha)
        run.parent.log('mse', mse)

        model_name = 'ridge_{0:.2f}'.format(alpha)
        model_file_name = f'{model_name}.pkl'
        model_path = os.path.join(model_output_dir, model_file_name)

        # save model in the outputs folder so it automatically get uploaded
        joblib.dump(value=reg, filename=model_path)

        # Upload model to run
        run.upload_file(model_name, model_path)

        # Register model in the outputs folder so it automatically get uploaded
        model = run.register_model(model_name=model_name,               # Name of the to-be-registered model
                        model_path=model_name,                       # Reference to the model file within the run context
                        model_framework=Model.Framework.SCIKITLEARN, # Framework used to create the model.
                        model_framework_version=sklearnver,          # Version of scikit-learn used to create the model.
                        datasets=[("train_X", X_ds), ("train_Y", y_ds)],
                        sample_input_dataset=X_ds,
                        sample_output_dataset=y_ds,
                        resource_configuration=ResourceConfiguration(cpu=1, memory_in_gb=0.5),
                        description='Ridge regression model to predict diabetes progression.',
                        tags={'area': 'diabetes', 'type': 'regression'})

        print('Name:', model.name)
        print('Version:', model.version)

        print('alpha is {0:.2f}, and mse is {1:0.2f}'.format(alpha, mse))

if __name__ == "__main__":
    train()
