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

    # Try relative path w.r.t. the current working directory
    local = os.path.join(os.getcwd(), filename)
    if os.path.exists(local):
        return local

    # Try relative path w.r.t. the Python package base directory
    package = os.path.join(os.path.split(__file__)[0], "..", filename)
    if os.path.exists(package):
        return package

    # Try relative path w.r.t. the specified data directory
    indata = os.path.join(_data_dir, filename)
    if os.path.exists(indata):
        return indata

    raise FileNotFoundError(
        f"Cannot locate file {filename}, maybe use set_data_directory to point to the correct location."
    )


# Initialize paths when loading this module
_data_dir = os.getcwd()

if "JUPYTERHUB_USER" in os.environ and os.path.exists("/opt/filteradapt"):
    _data_dir = "/opt/filteradapt"
