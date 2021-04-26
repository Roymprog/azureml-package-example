#!/usr/bin/env python

import logging
from pathlib import Path

import click
from azureml.core import Workspace, Environment
from azureml.core.runconfig import RunConfiguration
from azureml.data.data_reference import DataReference
from azureml.pipeline.core import Pipeline, PipelineData
from azureml.pipeline.core.graph import PipelineParameter
from azureml.pipeline.steps import PythonScriptStep


# Needs to be here, as AzureML otherwise overrides our logging.
logging.basicConfig(
    format="[%(asctime)-15s] %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


# pylint: disable=too-many-arguments,too-many-locals,too-many-statements
@click.command()
@click.option("--workspace_name", required=True, envvar="ML_WORKSPACE_NAME")
@click.option("--subscription_id", required=True, envvar="SUBSCRIPTION_ID")
@click.option("--resource_group", required=True, envvar="ML_RESOURCE_GROUP")
@click.option("--pipeline_name", required=True, envvar="ML_PIPELINE_NAME")
@click.option("--pipeline_version", required=True, envvar="ML_PIPELINE_VERSION")
@click.option("--pipeline_description", default="")
@click.option("--model_dir", default="model")
@click.option("--compute_name", required=True, envvar="AML_COMPUTE_CLUSTER_NAME")
@click.option("--vm_size", required=True, envvar="AML_COMPUTE_CLUSTER_CPU_SKU")
@click.option("--vm_min_nodes", required=True, envvar="AML_CLUSTER_MIN_NODES")
@click.option("--vm_max_nodes", required=True, envvar="AML_CLUSTER_MAX_NODES")
@click.option(
    "--pipeline_id_path",
    default=None,
    type=Path,
    help="Output file to write the ID of the published pipeline to.",
)
@click.option("--default_name", required=True, envvar="MODEL_DEFAULT_NAME") # Example of default parameter
@click.option("--dry-run/--no-dry-run", default=False)
def main(
    workspace_name,
    subscription_id,
    resource_group,
    pipeline_name,
    pipeline_description,
    pipeline_version,
    model_dir,
    compute_name,
    vm_size,
    vm_min_nodes,
    vm_max_nodes,
    pipeline_id_path,
    default_name,
    dry_run,
):
    """Publishes the models ML pipeline to Azure ML."""

    # Some custom parameter.
    name = PipelineParameter("name", default_value=default_name)

    # Get Azure machine learning workspace
    workspace = Workspace.get(
        name=workspace_name,
        subscription_id=subscription_id,
        resource_group=resource_group,
    )
    logging.info("Using workspace: %s", repr(workspace))

    # Get Azure machine learning cluster
    compute_target = get_or_create_compute_target(
        workspace,
        compute_name,
        vm_size=vm_size,
        min_nodes=vm_min_nodes,
        max_nodes=vm_max_nodes,
    )

    # Setup run environment (with private wheels + Docker).
    run_config = RunConfiguration()
    run_config.environment = Environment.from_conda_specification(
        "model-env",
        "model/environment.yml"
    )

    # Allow users to supply their own Docker file.
    docker_path = Path(model_dir) / "Dockerfile"
    if docker_path.exists():
        with open(docker_path) as fp:
            docker_file = fp.read()

        run_config.environment.docker.enabled = True
        run_config.environment.docker.base_image = None
        run_config.environment.docker.base_dockerfile = docker_file

    logging.info("Using environment: %s", repr(run_config.environment))


    example_step = PythonScriptStep(
        name="Example step",
        source_directory=model_dir,
        script_name="scripts/my_script.py",
        arguments=[
            "--name",
            name
        ],
        runconfig=run_config,
        compute_target=compute_target,
        inputs=[evaluation_data],
    )

    evaluate_performance_step.run_after(upload_predictions_step)

    pipeline = Pipeline(
        workspace=workspace,
        steps=[example_step],
    )
    pipeline.validate()

    if not dry_run:
        published_pipeline = pipeline.publish(
            name=pipeline_name,
            description=pipeline_description,
            continue_on_step_failure=False,
            version=pipeline_version,
        )

        if pipeline_id_path:
            with pipeline_id_path.open("w") as file_:
                print(published_pipeline.id, file=file_)

        logging.info(
            f"Published pipeline {published_pipeline.id} with name "
            f"{published_pipeline.name} with version {published_pipeline.version}"
        )


# pylint: disable=too-many-locals
def get_or_create_compute_target(
    workspace: "azureml.core.Workspace",
    name: str,
    *,
    vm_size: str = "STANDARD_D2_V2",
    vm_priority: str = "dedicated",
    min_nodes: int = 0,
    max_nodes=1,
    idle_seconds_before_scaledown: str = "300",
    wait: bool = False,
    wait_timeout: int = 10,
    vnet_name: str = None,
    vnet_resourcegroup_name: str = None,
    subnet_name: str = None,
    tags: Dict[str, str] = None,
    description: str = None,
):
    """
    Fetches a compute target (VM cluster) from the given workspace by name,
    if exists. If a compute target with the given name doesn't exist, it is
    created with the given settings.

    Parameters
    ----------
    worskpace
        AzureML workspace to get-or-create compute target from.
    name
        Name of the compute target.
    vm_size
        Size to use for the VMs.
    vm_priority
        Priority to use for VMs (dedicated, or low-priority).
    min_nodes
        Minimum number of nodes to have running in the cluster.
    max_nodes
        Maximum number of nodes to scale the cluster up to.
    idle_seconds_before_scaledown
        Number of seconds to wait before scaling down when idle.
    wait
        Whether to wait for the creation of the cluster to finish.
    wait_timeout
        Maximum number of minutes to wait for the creation of the cluster.
    vnet_name
        Name of the virtual network (vnet) to place the cluster in.
    vnet_resourcegroup_name
        Name of the resource group where the virtual network is located
    subnet_name
        Name of the subnet to attach the cluster to (should be inside the vnet).
    tags
        Dictionary of key value tags to attach to the compute object.
    description
        Description to attach to the compute object.

    Raises
    ------
    ComputeTargetException

    Returns
    -------
    azureml.core.compute.ComputeTarget
        An AML ComputeTarget instance
    """

    try:
        from azureml.core.compute import ComputeTarget, AmlCompute
    except ImportError:
        raise ImportError("azureml-core needs to be installed to use this function")

    logger = logging.getLogger(__name__)

    try:
        # Try to get existing compute target.
        target = workspace.compute_targets[name]
        logger.info("Using existing compute target %r", name)
    except KeyError:
        # Doesn't exist, create a new one.
        logger.info("Creating new compute target %r", name)

        config = AmlCompute.provisioning_configuration(
            vm_size=vm_size,
            vm_priority=vm_priority,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            idle_seconds_before_scaledown=idle_seconds_before_scaledown,
            vnet_resourcegroup_name=vnet_resourcegroup_name,
            vnet_name=vnet_name,
            subnet_name=subnet_name,
            tags=tags,
            description=description,
        )
        target = ComputeTarget.create(
            workspace, name=name, provisioning_configuration=config
        )

        if wait:
            target.wait_for_completion(timeout_in_minutes=wait_timeout)

    return target


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
