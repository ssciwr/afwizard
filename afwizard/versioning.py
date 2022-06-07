from afwizard.utils import AFwizardError


# Define the current major version of the filter data model defined
# by AFwizard. This number should be increased whenever there
# is a *non-backwards compatible* change in the data model. It invalidates
# any filters being written for prior major versions. This is a drastic
# thing that should have very good, well discussed reasons. Still, it is
# important to build the possibility of such change into the data model early.
AFWIZARD_DATAMODEL_MAJOR_VERSION = 0

# Define the current minor version of the filter data model defined by
# adaptivefiltering. This number should be increased whenever there is a
# change to the model e.g. the addition or renaming of metadata. When
# increasing this number you should also add an upgrade function that allows
# adaptivefiltering to port existing filters to the new minor version.
AFWIZARD_DATAMODEL_MINOR_VERSION = 0

# A global registry of update functions
_upgrade_functions = {}


def upgrade_function(major, minor):
    """A decorator to use to mark an upgrade function.

    Upgrade functions are expected to take a JSON configuration
    as their only argument and return a modified JSON.

    :param major:
        The major version to upgrade from
    :param minor:
        The minor version to upgrade from
    """

    def _decorator(func):
        _upgrade_functions[major, minor] = func
        return func

    return _decorator


def upgrade_filter(data):
    """Upgrades a given filter configuration to the current data model version"""
    # If this is an incompatible major version, we throw an error
    if data["_major"] != AFWIZARD_DATAMODEL_MAJOR_VERSION:
        raise AFwizardError("Loading an outdated filter")

    # If the filter is newer than the version of adaptivefiltering we also throw
    if data["_minor"] > AFWIZARD_DATAMODEL_MINOR_VERSION:
        raise AFwizardError(
            "Update your version of adaptivefiltering to use this filter"
        )

    for minor in range(data["_minor"], AFWIZARD_DATAMODEL_MINOR_VERSION):
        data = _upgrade_functions[AFWIZARD_DATAMODEL_MAJOR_VERSION, minor](data)

    return data


#
# In the following all upgrade functions to the afwizard data model are implemented.
#
# A potential first upgrade function could look like this:
#
# @upgrade_function(0, 0)
# def add_keywords_field(config):
#     config["keywords"] = []
#     return config
#
