# -*- coding: utf-8 -*-
import re
import typing
from functools import wraps

from pre_commit_scripts.language_formatters_pre_commit_hooks.utils import run_command


F = typing.TypeVar("F", bound=typing.Callable[..., int])


def _is_command_success(
    *command_args: str,
) -> bool:
    exit_status, _, _ = run_command(*command_args)
    return exit_status == 0


class ToolNotInstalled(RuntimeError):
    def __init__(self, tool_name: str, download_install_url: str) -> None:
        self.tool_name = tool_name
        self.download_install_url = download_install_url

    def __str__(self) -> str:
        return str(
            "{tool_name} is required to run this pre-commit hook.\n"
            "Make sure that you have it installed and available on your path.\n"
            "Download/Install URL: {download_install_url}".format(
                tool_name=self.tool_name,
                download_install_url=self.download_install_url,
            )
        )


class _ToolRequired:
    def __init__(
        self,
        tool_name: str,
        check_command: typing.Callable[[typing.Optional[typing.Mapping[str, typing.Any]]], bool],
        download_install_url: str,
        extras: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    ) -> None:
        self.tool_name = tool_name
        self.check_command = check_command
        self.download_install_url = download_install_url
        self.extras = extras

    def is_tool_installed(self) -> bool:
        return self.check_command(self.extras)

    def assert_tool_installed(self) -> None:
        if not self.is_tool_installed():
            raise ToolNotInstalled(
                tool_name=self.tool_name,
                download_install_url=self.download_install_url,
            )

    def __call__(self, f: F) -> F:
        @wraps(f)
        def wrapper(*args: typing.Any, **kwargs: typing.Any) -> int:
            self.assert_tool_installed()
            return f(*args, **kwargs)

        return wrapper  # type: ignore


java_required = _ToolRequired(
    tool_name="JRE",
    check_command=lambda _: _is_command_success("java", "-version"),
    download_install_url="https://www.java.com/en/download/",
)

class UnableToVerifyJDKVersion(RuntimeError):
    def __str__(self) -> str:
        return "Unable to verify the JDK version"  # pragma: no cover

