from typing import Dict, Iterable, Optional, Tuple

import click
from requests.auth import HTTPDigestAuth

from .. import runner, utils
from ..types import Filter
from ..utils import dict_true_values
from . import output, validators

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

DEFAULT_CHECKS_NAMES = tuple(check.__name__ for check in runner.DEFAULT_CHECKS)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def main() -> None:
    """Command line tool for testing your web application built with Open API / Swagger specifications."""


@main.command(short_help="Perform schemathesis test.")
@click.argument("schema", type=str, callback=validators.validate_schema)  # type: ignore
@click.option(
    "--checks",
    "-c",
    multiple=True,
    help="List of checks to run.",
    type=click.Choice(DEFAULT_CHECKS_NAMES),
    default=DEFAULT_CHECKS_NAMES,
)
@click.option(  # type: ignore
    "--auth",
    "-a",
    help="Server user and password. Example: USER:PASSWORD",
    type=str,
    callback=validators.validate_auth,  # type: ignore
)
@click.option(  # type: ignore
    "--auth-type",
    "-A",
    type=click.Choice(["basic", "digest"], case_sensitive=False),
    default="basic",
    help="The authentication mechanism to be used. Defaults to 'basic'.",
)
@click.option(  # type: ignore
    "--header",
    "-H",
    "headers",
    help=r"Custom header in a that will be used in all requests to the server. Example: Authorization: Bearer\ 123",
    multiple=True,
    type=str,
    callback=validators.validate_headers,  # type: ignore
)
@click.option(
    "--endpoint",
    "-E",
    "endpoints",
    type=str,
    multiple=True,
    help=r"Filter schemathesis test by endpoint pattern. Example: users/\d+",
)
@click.option("--method", "-M", "methods", type=str, multiple=True, help="Filter schemathesis test by HTTP method.")
@click.option("--base-url", "-b", help="Base URL address of the API.", type=str)
def run(  # pylint: disable=too-many-arguments
    schema: str,
    auth: Optional[Tuple[str, str]],
    auth_type: str,
    headers: Dict[str, str],
    checks: Iterable[str] = DEFAULT_CHECKS_NAMES,
    endpoints: Optional[Filter] = None,
    methods: Optional[Filter] = None,
    base_url: Optional[str] = None,
) -> None:
    """Perform schemathesis test against an API specified by SCHEMA.

    SCHEMA must be a valid URL pointing to an Open API / Swagger specification.
    """
    selected_checks = tuple(check for check in runner.DEFAULT_CHECKS if check.__name__ in checks)

    click.echo("Running schemathesis test cases ...")

    if auth and auth_type == "digest":
        auth = HTTPDigestAuth(*auth)  # type: ignore

    options = dict_true_values(
        api_options=dict_true_values(base_url=base_url, auth=auth, headers=headers),
        loader_options=dict_true_values(endpoint=endpoints, method=methods),
    )

    with utils.stdout_listener() as get_stdout:
        stats = runner.execute(schema, checks=selected_checks, **options)
        hypothesis_out = get_stdout()

    output.pretty_print_stats(stats, hypothesis_out=hypothesis_out)
    click.echo()

    if any(value.get("error") for value in stats.data.values()):
        click.echo(click.style("Tests failed.", fg="red"))
        raise click.exceptions.Exit(1)

    click.echo(click.style("Tests succeeded.", fg="green"))