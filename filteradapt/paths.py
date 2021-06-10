import os

# Storage for the data directory that will be used to resolve relative paths
_data_dir = None


def set_data_directory(directory):
    global _data_dir
    _data_dir = directory


def locate_file(filename):
    # If the path is absolute, do not change it
    if os.path.isabs(filename):
        return filename

    # Gather a list of candidate paths for relative path
    candidates = [
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.split(__file__)[0], "..", filename),
        os.path.join(_data_dir, filename),
    ]

    # Iterate through the list to check for file existence
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(
        f"Cannot locate file {filename}, maybe use set_data_directory to point to the correct location. Tried the following: {', '.join(candidates)}"
    )


# Initialize paths when loading this module
_data_dir = os.getcwd()

if "JUPYTERHUB_USER" in os.environ and os.path.exists("/opt/filteradapt"):
    _data_dir = "/opt/filteradapt"
