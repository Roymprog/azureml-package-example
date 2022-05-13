from azureml.core.authentication import InteractiveLoginAuthentication
from azureml.core import Workspace
from azureml.pipeline.core import PublishedPipeline
import requests
import click
import logging 

@click.command()
@click.option("--workspace_name", required=True, envvar="ML_WORKSPACE_NAME")
@click.option("--subscription_id", required=True, envvar="SUBSCRIPTION_ID")
@click.option("--resource_group", required=True, envvar="ML_RESOURCE_GROUP")
@click.option("--pipeline_id", required=True, envvar="ML_PIPELINE_ID")
@click.option("--experiment_name", required=True, envvar="ML_EXPERIMENT_NAME")
def main(
    workspace_name,
    subscription_id,
    resource_group,
    pipeline_id,
    experiment_name,
):
    """Triggers an ML pipeline in Azure ML using its REST API endpoint."""

    # Get Azure machine learning workspace
    ws = Workspace.get(
        name=workspace_name,
        subscription_id=subscription_id,
        resource_group=resource_group,
    )
    logging.info("Using workspace: %s", repr(ws))

    auth = InteractiveLoginAuthentication()
    aad_token = auth.get_authentication_header()

    published_pipeline = PublishedPipeline.get(ws, pipeline_id)
    published_pipeline

    rest_endpoint = "https://westeurope.api.azureml.ms/pipelines/v1.0/subscriptions/8e155238-93f7-4377-9b62-6a2f4e51052e/resourceGroups/roy-van-santen-sandbox/providers/Microsoft.MachineLearningServices/workspaces/roy-van-santen/PipelineRuns/PipelineSubmit/b7c88abc-58d4-4615-9e42-4e373a5c7435" 

    print(
        "You can perform HTTP POST on URL {} to trigger this pipeline".format(rest_endpoint)
    )

    # specify the param when running the pipeline
    response = requests.post(
        rest_endpoint,
        headers=aad_token,
        json={
            "ExperimentName": experiment_name,
            "RunSource": "SDK",
            "ParameterAssignments": {},
        },
    )

    try:
        response.raise_for_status()
    except Exception:
        raise Exception(
            "Received bad response from the endpoint: {}\n"
            "Response Code: {}\n"
            "Headers: {}\n"
            "Content: {}".format(
                rest_endpoint, response.status_code, response.headers, response.content
            )
        )

    run_id = response.json().get("Id")
    print("Submitted pipeline run: ", run_id)

if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
