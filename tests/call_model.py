# azureml-core of version 1.0.72 or higher is required
# azureml-dataprep[pandas] of version 1.1.34 or higher is required
from azureml.core import Workspace, Dataset
import requests
import json
import click

@click.command()
@click.option("--workspace_name", required=True, envvar="ML_WORKSPACE_NAME")
@click.option("--subscription_id", required=True, envvar="SUBSCRIPTION_ID")
@click.option("--resource_group", required=True, envvar="ML_RESOURCE_GROUP")
@click.option("--model_url", required=True, envvar="ML_MODEL_URL")
@click.option("--model_dataset_name", required=True, envvar="ML_MODEL_DATASET_NAME")
@click.option("--model_dataset_version", required=True, envvar="ML_MODEL_DATASET_VERSION")
@click.option("--api_key", required=True, envvar="ML_MODEL_SERVICE_API_KEY")
def main(
    workspace_name,
    subscription_id,
    resource_group,
    model_url,
    model_dataset_name,
    model_dataset_version,
    api_key,
):
    """Call model running as an Azure service."""

    # Connect to workspace to get data from dataset
    workspace = Workspace(subscription_id, resource_group, workspace_name)

    dataset = Dataset.get_by_name(workspace, name=model_dataset_name, version=model_dataset_version)
    df = dataset.to_pandas_dataframe()

    data = json.dumps({
        'data': df[:2].to_numpy().tolist(),
        'method': 'predict'
    })

    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}

    resp = requests.post(model_url, data, headers=headers)
    print(resp.text)

if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
