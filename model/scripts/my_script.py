import click

import my_package


@click.command()
@click.option("--name", default="world")
def main(name):
    click.echo(f"Hello {name}!")


# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    setup_logging()
    main()
