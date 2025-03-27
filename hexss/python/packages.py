import subprocess
from importlib.metadata import version as get_version, packages_distributions
import re
from typing import Sequence, List, Set, Tuple

import hexss
from hexss.constants.terminal_color import *
from hexss.path import get_python_path

# Map package aliases to actual package names for installation
PACKAGE_ALIASES = {
    # 'install_name': 'freeze_name'
    'pygame-gui': 'pygame_gui'
}


def get_installed_packages(python_path=get_python_path()) -> Set[Tuple[str, str]]:
    """
    Retrieves a set of installed Python packages (name and version tuples)
    using pip and importlib.metadata.
    """
    output = subprocess.check_output([
        str(python_path), "-c",
        "import importlib.metadata\n"
        "for dist in importlib.metadata.distributions():\n"
        " print(dist.name, dist.version, sep='==')"
    ], text=True)

    packages: List[Tuple[str, str]] = []
    for line in output.splitlines():
        if '==' in line:
            name, version = line.split('==')
            packages.append((name.strip(), version.strip()))
    return set(packages)


def parse_version(version: str) -> Tuple:
    return tuple(map(int, re.findall(r'\d+', version)))


def version_satisfies(version: str, specifier: str) -> bool:
    if not specifier:
        return True
    if specifier.startswith("=="):
        return parse_version(version) == parse_version(specifier[2:])
    elif specifier.startswith(">="):
        return parse_version(version) >= parse_version(specifier[2:])
    elif specifier.startswith("<="):
        return parse_version(version) <= parse_version(specifier[2:])
    elif specifier.startswith(">"):
        return parse_version(version) > parse_version(specifier[1:])
    elif specifier.startswith("<"):
        return parse_version(version) < parse_version(specifier[1:])
    return False


def missing_packages(*packages: str) -> List[str]:
    """
    Identifies missing packages from the list of required packages,
    including support for version specifiers.

    Requirements are parsed using packaging.requirements.Requirement.

    Examples:
        missing_packages('numpy', 'opencv-python')
        missing_packages('numpy==2', 'opencv-python')
        missing_packages('numpy==2.0.0', 'opencv-python')
        missing_packages('numpy>=2.0.0', 'opencv-python')
    """
    installed_dict = {name.lower(): version for name, version in get_installed_packages()}

    missing = []
    for req in packages:
        match = re.match(r"([a-zA-Z0-9_-]+)([<>=!]*)([\dA-Za-z.+!_-]*)", req)
        if not match:
            missing.append(req)
            continue

        pkg_name, operator, version = match.groups()
        actual_pkg = PACKAGE_ALIASES.get(pkg_name, pkg_name)
        actual_pkg_lower = actual_pkg.lower()

        installed_version = installed_dict.get(actual_pkg_lower)
        # Package is not installed
        if installed_version is None:
            missing.append(req)
            continue

        if not version_satisfies(installed_version, operator + version):
            missing.append(req)
    return missing


def generate_install_command(
        packages: Sequence[str], upgrade: bool = False, proxy: str = None
) -> List[str]:
    """
    Generates the pip install command based on the specified packages.
    """
    command = [str(get_python_path()), "-m", "pip", "install"]
    if proxy or (hexss.proxies and hexss.proxies.get('http')):  # Add proxy if available
        command.append(f"--proxy={proxy or hexss.proxies['http']}")
    if upgrade:
        command.append("--upgrade")
    command.extend(packages)
    return command


def run_command(command: List[str], verbose: bool = False) -> int:
    """
    Executes a given command in a subprocess and returns the exit code.
    """
    try:
        if verbose:
            print(f"{BLUE}Executing: {BOLD}{' '.join(command)}{END}")
            result = subprocess.run(command, check=True)
        else:
            result = subprocess.run(command, capture_output=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"{RED}Command failed with error: {e}{END}")
        return e.returncode


def install(*packages: str, verbose: bool = True) -> None:
    """
    Installs missing packages.
    """
    missing = missing_packages(*packages)
    if not missing:
        if verbose: print(f"{GREEN}All specified packages are already installed.{END}")
        return
    if verbose: print(f"{YELLOW}Installing: {BOLD}{', '.join(missing)}{END}")
    command = generate_install_command(missing)
    if run_command(command, verbose=verbose) == 0:
        if verbose: print(f"{GREEN.BOLD}{', '.join(packages)}{END} {GREEN}installation complete.{END}")
    else:
        print(f"{RED}Failed to install {BOLD}{', '.join(packages)}{END}. {RED}Check errors.{END}")


def install_upgrade(*packages: str, verbose: bool = True) -> None:
    """
    Installs or upgrades the specified packages.
    """
    # if verbose: print(f"{PINK}Upgrading pip...{END}")
    # pip_command = generate_install_command(["pip"], upgrade=True)
    # run_command(pip_command, verbose=verbose)
    if verbose: print(f"{YELLOW}Installing or upgrading: {BOLD}{' '.join(packages)}{END}")
    command = generate_install_command(packages, upgrade=True)
    if run_command(command, verbose=verbose) == 0:
        if verbose: print(f"{GREEN.BOLD}{', '.join(packages)}{END} {GREEN}installation/upgrade complete.{END}")
    else:
        print(f"{RED}Failed to install/upgrade {BOLD}{', '.join(packages)}{END}. {RED}Check errors.{END}")


def check_packages(*packages: str, auto_install: bool = False, verbose: bool = True) -> None:
    """
    Checks if the required Python packages are installed (and meet any version constraints).
    Optionally, installs missing packages automatically if auto_install is set to True.
    """
    missing = missing_packages(*packages)
    if not missing:
        # if verbose: print(f"{GREEN}All specified packages are already installed.{END}")
        return

    if auto_install:
        print(f"{PINK}Missing packages detected. Attempting to install: {BOLD}{', '.join(missing)}{END}")
        for package in missing:
            install(package, verbose=verbose)
        # Recursively check packages again
        check_packages(*packages)
    else:
        try:
            raise ImportError(
                f"{RED.BOLD}The following packages are missing:{END.RED} "
                f"{ORANGE.UNDERLINED}{', '.join(missing)}{END}\n"
                f"{RED}Install them manually or set auto_install=True.{END}"
            )
        except ImportError as e:
            print(e)
            exit()


if __name__ == "__main__":
    # test

    operators = ['==', '>=', '<=', '>', '<']

    versions = [
        # Various development release incarnations
        "1.0dev",
        "1.0.dev",
        "1.0dev1",
        "1.0-dev",
        "1.0-dev1",
        "1.0DEV",
        "1.0.DEV",
        "1.0DEV1",
        "1.0.DEV1",
        "1.0-DEV",
        "1.0-DEV1",
        # Various alpha incarnations
        "1.0a",
        "1.0.a",
        "1.0.a1",
        "1.0-a",
        "1.0-a1",
        "1.0alpha",
        "1.0.alpha",
        "1.0.alpha1",
        "1.0-alpha",
        "1.0-alpha1",
        "1.0A",
        "1.0.A",
        "1.0.A1",
        "1.0-A",
        "1.0-A1",
        "1.0ALPHA",
        "1.0.ALPHA",
        "1.0.ALPHA1",
        "1.0-ALPHA",
        "1.0-ALPHA1",
        # Various beta incarnations
        "1.0b",
        "1.0.b",
        "1.0.b1",
        "1.0-b",
        "1.0-b1",
        "1.0beta",
        "1.0.beta",
        "1.0.beta1",
        "1.0-beta",
        "1.0-beta1",
        "1.0B",
        "1.0.B",
        "1.0.B1",
        "1.0-B",
        "1.0-B1",
        "1.0BETA",
        "1.0.BETA",
        "1.0.BETA1",
        "1.0-BETA",
        "1.0-BETA1",
        # Various release candidate incarnations
        "1.0c",
        "1.0.c",
        "1.0.c1",
        "1.0-c",
        "1.0-c1",
        "1.0rc",
        "1.0.rc",
        "1.0.rc1",
        "1.0-rc",
        "1.0-rc1",
        "1.0C",
        "1.0.C",
        "1.0.C1",
        "1.0-C",
        "1.0-C1",
        "1.0RC",
        "1.0.RC",
        "1.0.RC1",
        "1.0-RC",
        "1.0-RC1",
        # Various post release incarnations
        "1.0post",
        "1.0.post",
        "1.0post1",
        "1.0-post",
        "1.0-post1",
        "1.0POST",
        "1.0.POST",
        "1.0POST1",
        "1.0.POST1",
        "1.0-POST",
        "1.0-POST1",
        "1.0-5",
        # Local version case insensitivity
        "1.0+AbC"
        # Integer Normalization
        "1.01",
        "1.0a05",
        "1.0b07",
        "1.0c056",
        "1.0rc09",
        "1.0.post000",
        "1.1.dev09000",
        "00!1.2",
        "0100!0.0",
        # Various other normalizations
        "v1.0",
    ]

    pkg_names = ['google_tran-s', 'opencv-python', 'aa_aa']

    test_results = 'OK'
    for pkg_name in pkg_names:
        for operator in operators:
            for version in versions:
                req = f'{pkg_name}{operator}{version}'
                match = re.match(r"([a-zA-Z0-9_-]+)([<>=!]*)([\dA-Za-z.+!_-]*)", req)

                pkg_name_, operator_, version_ = match.groups()

                if pkg_name_ != pkg_name or operator_ != operator or version_ != version:
                    print(req)
                    print(pkg_name_)
                    print(operator_)
                    print(version_)
                    print()

                    test_results = 'not OK'

    print(test_results)
