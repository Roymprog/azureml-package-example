from azureml.core.compute import AksCompute, ComputeTarget
from azureml.core import Workspace
from azureml.core.compute_target import ComputeTargetException
from azureml.core.webservice import AksWebservice
from azureml.core.model import Model
import click
import logging 

@click.command()
@click.option("--workspace_name", required=True, envvar="ML_WORKSPACE_NAME")
@click.option("--subscription_id", required=True, envvar="SUBSCRIPTION_ID")
@click.option("--resource_group", required=True, envvar="ML_RESOURCE_GROUP")
@click.option("--model_name", required=True, envvar="ML_MODEL_NAME")
@click.option("--model_version", required=True, envvar="ML_MODEL_VERSION")
@click.option("--aks_cluster_name", required=True, envvar="AKS_CLUSTER_NAME")
def main(
    workspace_name,
    subscription_id,
    resource_group,
    model_name,
    model_version,
    aks_cluster_name,
):
    """Deploy model to (pre-existing) AKS cluster"""

    # Get Azure machine learning workspace
    ws = Workspace.get(
        name=workspace_name,
        subscription_id=subscription_id,
        resource_group=resource_group,
    )
    logging.info("Using workspace: %s", repr(ws))

    # Create AKS cluster with name if it doesn't exist
    try:
        aks_target = ComputeTarget(workspace=ws, name=aks_cluster_name)
        print('Found existing cluster, use it.')
    except ComputeTargetException:
        prov_config = AksCompute.provisioning_configuration(cluster_purpose = AksCompute.ClusterPurpose.DEV_TEST)
        # Create the DEV_TEST cluster (takes ~10 minutes)
        aks_target = ComputeTarget.create(workspace = ws,
                                        name = aks_cluster_name,
                                        provisioning_configuration = prov_config)

        # Wait for the create process to complete
        aks_target.wait_for_completion(show_output = True)

    # Find model in workspace
    model = Model(workspace=ws, name=model_name, version=model_version)

    # Deploy model to AKS using no-code-deployment
    deployment_config = AksWebservice.deploy_configuration(cpu_cores = 1, memory_gb = 1)

    service = Model.deploy(ws, "model-service-aks", [model], deployment_config=deployment_config, deployment_target=aks_target)

    service.wait_for_deployment(show_output = True)

    print(service.state)
    print(service.get_logs())

if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
