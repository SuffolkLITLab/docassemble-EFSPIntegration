# do not pre-load
# Import plugin hooks before importing DAL stuff that uses it

import pluggy
import pytest

import docassemble.base.hooks
from docassemble.base.plugin_manager import pm
from docassemble.base.thread_context import empty_globals, global_context

hookimpl = pluggy.HookimplMarker("docassemble")


class Mocks:
    @hookimpl
    def get_configuration() -> dict:  # type: ignore
        """
        Get configuration

        Returns:
            An empty dictionary
        """
        return {}

    @hookimpl
    def file_finder(file_reference) -> dict:
        """
        Default file finder

        Returns:
            Easiest implementation of files in a package.
        """
        return {"fullpath": file_reference.replace(".", "/").replace(":", "/")}  # type: ignore

    @hookimpl
    def get_default_timezone() -> str:  # type: ignore
        """
        Default timezone

        Returns:
            String for NYC timezone.
        """
        return "America/New_York"


if not pm.is_registered(Mocks):
    pm.register(Mocks)


@pytest.fixture(autouse=True)
def docassemble_context():
    """Give each test its own `this_thread`, so state can't leak between them."""
    with global_context(empty_globals()):
        yield
