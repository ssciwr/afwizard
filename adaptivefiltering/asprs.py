from adaptivefiltering.utils import AdaptiveFilteringError


import functools


class ASPRSClassification:
    """A data structure that describes the ASPRS Standard Lidar Point Classes"""

    @functools.lru_cache
    def _mapping(cls):
        """Mapping of string names to classification values.

        This only exposes the subset relevant to our use cases
        """
        return {
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

    def __getitem__(self, class_):
        """Create a classification value sequence from input"""

        # This might be a slice, which we will resolve to an integer sequence
        if isinstance(class_, slice):
            # If start is not given, it is zero
            start = class_.start
            if start is None:
                start = 0

            # If stop is not given, it is the maximum possible classification value: 255
            stop = class_.stop
            if stop is None:
                stop = 255
            # This adaptation is necessary to be able to use the range generator below
            stop = stop + 1

            # Collect the list of arguments to the range generator
            args = [start, stop]

            # Add a third parameter iff the slice step parameter was given
            if class_.step is not None:
                args.append(class_.step)

            # Return the tuple of classification values
            return tuple(range(*args))

        def _process_list_item(item):
            """Process a single given classification value"""
            if isinstance(item, str):
                # If this is a string we try to split it at commas
                subitems = item.split(",")
                if len(subitems) > 1:
                    # If a comma-separated list was given, we return the union of classification
                    # values for each of the entries of that list
                    return sum((_process_list_item(i.strip()) for i in subitems), ())
                else:
                    try:
                        # For strings, we do a lookup in our internal name mapping
                        return self._mapping()[item.strip()]
                    except KeyError:
                        raise AdaptiveFilteringError("Classifier not known")

            # If no string was given, we assume that a plain integer was given
            assert isinstance(item, int)

            # Check whether the value is in the interval [0, 255]
            if item < 0 or item > 255:
                raise AdaptiveFilteringError(
                    "Classification values need to be in the interval [0, 255]"
                )

            return (item,)

        def _sort_uniq(items):
            return tuple(sorted(set(items)))

        # If a tuple of items was given, we return the union of classification values
        if isinstance(class_, tuple):
            return _sort_uniq(sum((_process_list_item(i) for i in class_), ()))
        else:
            return _sort_uniq(_process_list_item(class_))


# A global object of type ASPRSClassification is available for simple use
asprs = ASPRSClassification()
