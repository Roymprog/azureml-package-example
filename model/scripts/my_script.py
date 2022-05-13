# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from azureml.core.run import Run
from azureml.core import Dataset, Model
from azureml.core.resource_configuration import ResourceConfiguration

import os
import numpy as np
from sklearn import __version__ as sklearnver
from packaging.version import Version
if Version(sklearnver) < Version("0.23.0"):
    from sklearn.externals import joblib
else:
    import joblib

os.makedirs('./outputs', exist_ok=True)

X, y = load_diabetes(return_X_y=True)

run = Run.get_context()

# Save and register Datasets
np.savetxt('features.csv', X, delimiter=',')
np.savetxt('labels.csv', y, delimiter=',')

ws = run.experiment.workspace
datastore = ws.get_default_datastore()
datastore.upload_files(files=['./features.csv', './labels.csv'],
                       target_path='sklearn_regression/',
                       overwrite=False)

input_data = Dataset.Tabular.from_delimited_files(path=[(datastore, 'sklearn_regression/features.csv')])
input_dataset = input_data.register(workspace=ws,
                    name='sklearn_regression_features',
                    create_new_version=True)
output_data = Dataset.Tabular.from_delimited_files(path=[(datastore, 'sklearn_regression/labels.csv')])
output_dataset = output_data.register(workspace=ws,
                    name='sklearn_regression_labels',
                    create_new_version=True)

X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                    test_size=0.2,
                                                    random_state=0)
data = {"train": {"X": X_train, "y": y_train},
        "test": {"X": X_test, "y": y_test}}

# list of numbers from 0.0 to 1.0 with a 0.05 interval
alphas = np.arange(0.0, 1.0, 0.05)

for alpha in alphas:
    # Use Ridge algorithm to create a regression model
    reg = Ridge(alpha=alpha)
    reg.fit(data["train"]["X"], data["train"]["y"])

    preds = reg.predict(data["test"]["X"])
    mse = mean_squared_error(preds, data["test"]["y"])
    run.log('alpha', alpha)
    run.log('mse', mse)

    model_file_name = 'ridge_{0:.2f}.pkl'.format(alpha)
    model_path = os.path.join('./outputs/', model_file_name)

    # save model in the outputs folder so it automatically get uploaded
    joblib.dump(value=reg, filename=model_path)

    # Register model in the outputs folder so it automatically get uploaded
    model = Model.register(workspace=ws,
                       model_name=model_file_name[:-4:],          # Name of the registered model in your workspace.
                       model_path=model_path,                # Local file to upload and register as a model.
                       model_framework=Model.Framework.SCIKITLEARN,  # Framework used to create the model.
                       model_framework_version=sklearnver,  # Version of scikit-learn used to create the model.
                       sample_input_dataset=input_dataset,
                       sample_output_dataset=output_dataset,
                       resource_configuration=ResourceConfiguration(cpu=1, memory_in_gb=0.5),
                       description='Ridge regression model to predict diabetes progression.',
                       tags={'area': 'diabetes', 'type': 'regression'})

    print('Name:', model.name)
    print('Version:', model.version)

    print('alpha is {0:.2f}, and mse is {1:0.2f}'.format(alpha, mse))
