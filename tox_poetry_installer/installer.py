"""Funcationality for performing virtualenv installation"""
# Silence this one globally to support the internal function imports for the proxied poetry module.
# See the docstring in 'tox_poetry_installer._poetry' for more context.
# pylint: disable=import-outside-toplevel
import concurrent.futures
import contextlib
import typing
from typing import Optional
from typing import Sequence
from typing import Set

import tox
from poetry.core.packages import Package as PoetryPackage
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import utilities

if typing.TYPE_CHECKING:
    from tox_poetry_installer import _poetry


def install(
    poetry: "_poetry.Poetry",
    venv: ToxVirtualEnv,
    packages: Sequence[PoetryPackage],
    parallels: Optional[int] = None,
):
    """Install a bunch of packages to a virtualenv

    :param poetry: Poetry object the packages were sourced from
    :param venv: Tox virtual environment to install the packages to
    :param packages: List of packages to install to the virtual environment
    :param parallels: Number of parallel processes to use for installing dependency packages, or
                      ``None`` to disable parallelization.
    """
    from tox_poetry_installer import _poetry

    tox.reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Installing {len(packages)} packages to environment at {venv.envconfig.envdir}"
    )

    pip = _poetry.PipInstaller(
        env=utilities.convert_virtualenv(venv),
        io=_poetry.NullIO(),
        pool=poetry.pool,
    )

    installed: Set[PoetryPackage] = set()

    @contextlib.contextmanager
    def _optional_parallelize():
        """A bit of cheat, really

        A context manager that exposes a common interface for the caller that optionally
        enables/disables the usage of the parallel thread pooler depending on the value of
        the ``parallels`` parameter.
        """
        if parallels:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=parallels
            ) as executor:
                yield executor.submit
        else:
            yield lambda func, arg: func(arg)

    with _optional_parallelize() as executor:
        for dependency in packages:
            if dependency not in installed:
                installed.add(dependency)
                tox.reporter.verbosity2(
                    f"{constants.REPORTER_PREFIX} Installing {dependency}"
                )
                executor(pip.install, dependency)
            else:
                tox.reporter.verbosity2(
                    f"{constants.REPORTER_PREFIX} Skipping {dependency}, already installed"
                )
        tox.reporter.verbosity2(
            f"{constants.REPORTER_PREFIX} Waiting for installs to finish..."
        )
