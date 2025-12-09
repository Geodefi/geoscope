# pylint: disable=import-outside-toplevel


def main() -> str:
    """
    Retrieve the current version of the Geoscope application.

    This function attempts to read the version from the `pyproject.toml` file
    using the `tomli` parser. If unsuccessful, it falls back to retrieving the version
    from the installed package metadata using `importlib.metadata`.

    If all attempts fail, it defaults to returning "1.0.0".

    Returns:
        str: The version of the Geoscope application.
    """
    try:
        from pathlib import Path

        # Attempt to read the version from pyproject.toml
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists() and pyproject_path.is_file():
            try:
                import tomli

                with pyproject_path.open("rb") as config_file:
                    toml_data = tomli.load(config_file)
                    version = toml_data["tool"]["poetry"]["version"]
                    return version
            except (tomli.TOMLDecodeError, KeyError) as e:
                print(
                    f"Geoscope: Failed to parse version from pyproject.toml: {e}. \
                        Falling back to package metadata."
                )
        else:
            print(
                (
                    f"Geoscope: pyproject.toml not found at {pyproject_path}."
                    "Falling back to package metadata.",
                )
            )

        # Fallback to importlib.metadata
        try:
            import importlib.metadata

            return importlib.metadata.version("Geoscope")
        except importlib.metadata.PackageNotFoundError as e:
            print(f"Geoscope package metadata not found: {e}. Falling back to default version.")

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        print(f"Unexpected error while retrieving version: {e}")

    # Default version if all else fails
    return "1.0.0"
