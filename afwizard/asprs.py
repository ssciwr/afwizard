from afwizard.utils import AFwizardError, is_iterable


# Mapping from human-readable name to class codes
_name_to_class = {
    "unclassified": (0, 1),
    "ground": (2,),
    "low_vegetation": (3,),
    "medium_vegetation": (4,),
    "high_vegetation": (5,),
    "building": (6,),
    "low_point": (7,),
    "water": (9,),
    "road_surface": (11,),
}


# Inverse mapping from class codes to human readable names
_class_to_name = ["(not implemented)"] * 256

# Populate the inverse mapping
for name, classes in _name_to_class.items():
    for c in classes:
        _class_to_name[c] = name


def asprs_class_code(name):
    """Map ASPRS classification name to code"""
    try:
        return _name_to_class[name]
    except KeyError:
        raise AFwizardError(
            f"Classification identifier '{name}'' not known to adaptivefiltering"
        )


def asprs_class_name(code):
    """Map ASPRS classification code to name"""
    try:
        return _class_to_name[code]
    except IndexError:
        raise AFwizardError(f"Classification code '{code}' not in range [0, 255]")


def asprs(vals):
    """Map a number of values to ASPRS classification codes

    :param vals:
        An arbitrary number of values that somehow describe an ASPRS
        code. Can be integers which will used directy, can be strings
        which will be split at commas and then turned into integers
    :returns:
        A sorted tuple of integers with ASPRS codes:
    :rtype: tuple
    """
    if is_iterable(vals):
        return tuple(sorted(set(sum((_asprs(v) for v in vals), ()))))
    else:
        return asprs([vals])


def _asprs(val):
    if isinstance(val, str):
        # First, we split at commas and go into recursion
        pieces = val.split(",")
        if len(pieces) > 1:
            return asprs(pieces)

        # If this is a simple string token it must match a code
        return asprs_class_code(pieces[0].strip())
    elif isinstance(val, int):
        if val < 0 or val > 255:
            raise AFwizardError(
                "Classification values need to be in the interval [0, 255]"
            )
        return (val,)
    elif isinstance(val, slice):
        # If start is not given, it is zero
        start = val.start
        if start is None:
            start = 0

        # If stop is not given, it is the maximum possible classification value: 255
        stop = val.stop
        if stop is None:
            stop = 255

        # This adaptation is necessary to be able to use the range generator below
        stop = stop + 1

        # Collect the list of arguments to the range generator
        args = [start, stop]

        # Add a third parameter iff the slice step parameter was given
        if val.step is not None:
            args.append(val.step)

        # Return the tuple of classification values
        return tuple(range(*args))
    else:
        raise ValueError(f"Cannot handle type {type(val)} in ASPRS classification")
