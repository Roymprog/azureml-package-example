from azureml.core.compute import ComputeTarget
from azureml.core import Run
from azureml.core.webservice import AksWebservice
from azureml.core.model import Model
import click

@click.command()
@click.option("--model_name", required=True)
@click.option("--model_version", required=True)
@click.option("--aks_cluster_name", required=True)
def deploy(
        model_name,
        model_version,
        aks_cluster_name,
    ):
    """Deploy model to existing AKS cluster"""

    run = Run.get_context()

    # Get Azure machine learning workspace
    ws = run.experiment.workspace
    print("Using workspace: %s", repr(ws))

    # Expects AKS cluster exists, raises otherwise
    aks_target = ComputeTarget(workspace=ws, name=aks_cluster_name)
    print('Found existing cluster, use it.')

    # Find model in workspace
    model = Model(workspace=ws, name=model_name, version=model_version)

    # Deploy model to AKS using no-code-deployment
    deployment_config = AksWebservice.deploy_configuration(cpu_cores = 1, memory_gb = 1)

    service = Model.deploy(ws, "model-service-aks", [model], deployment_config=deployment_config, deployment_target=aks_target)

    service.wait_for_deployment(show_output = True)

    return service

if __name__ == "__main__":
    deploy()
