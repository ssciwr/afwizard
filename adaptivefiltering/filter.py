from adaptivefiltering.utils import AdaptiveFilteringError
from adaptivefiltering.widgets import WidgetForm

import json
import jsonschema
import os
import pyrsistent


class FilterError(AdaptiveFilteringError):
    pass


class Filter:
    def __init__(self, config=None, filename=None):
        """The base class for a filter in adaptivefiltering

        A filter can either be constructed from a configuration or be deserialized
        from a file.

        :param config:
            The dictionary of configuration values that conforms to the schema
            defined by the schema property.
        :type config: dict
        :param filename:
            A filename to load the filter settings from. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str
        """
        if config is None and filename is None:
            raise FilterError(
                "Filters need to be constructed with either a configuration or a filename"
            )

        if config is not None:
            self.config = config

        if filename is not None:
            with open(os.path.abspath(filename)) as f:
                self.deserialize(f.read())

    # Store a registry of filter implementations derived from this base class
    _filter_impls = {}

    def __init_subclass__(cls, identifier=None):
        """Register all filter implementations that subclass this base class"""
        if identifier is None:
            raise FilterError("Please specify identifier when inheriting from filter")
        if identifier in Filter._filter_impls:
            raise FilterError(f"Filter identifier {identifier} already taken")
        Filter._filter_impls[identifier] = cls
        cls._identifier = identifier

    @property
    def config(self):
        """The configuration dictionary for this filter

        :type: pyrsistent.PMap
        """
        return self._config

    @config.setter
    def config(self, _config):
        jsonschema.validate(
            instance=pyrsistent.thaw(_config), schema=pyrsistent.thaw(self.schema)
        )
        self._config = pyrsistent.freeze(_config)

    def execute(self, dataset, inplace=False):
        """Apply the filter to a given data set

        :param dataset:
            The data set to apply the filter to.
        :type dataset: adaptivefiltering.DataSet
        :param inplace:
            Whether the filter application should be done in-place on the given
            data set. Defaults to False to allow an interactive filter application
            procedure.
        :type inplace: bool
        :return:
            A modified data set instance. This is the same object as the input data
            set if and only if the inplace parameter is true.
        """
        raise NotImplementedError

    def serialize(self):
        """Serialize this filter

        :return:
            The serialized string.
        :rtype: str
        """
        raise NotImplementedError

    def deserialize(self, data):
        """Deserialize this filter

        :param data:
            The data string from which to deserialize the filter
        :type data: str
        """
        raise NotImplementedError

    def save(self, filename):
        """Save this filter with its configuration to a file

        The resulting file can be read with the :func:`~adaptivefiltering.filter.Filter.load`
        method to restore this filter object.

        :param filename:
            The filename to save the filter to. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str
        """
        with open(os.path.abspath(filename)) as f:
            f.write(self.serialize())

    @property
    def schema(self):
        """Define the configuration schema for this filter

        :return:
            A nested dictionary data structure that contains the JSON schema
            for the configuration of this filter. The schema should conform to
            the Draft 7 JSON Schema standard (https://json-schema.org/).
        :rtype: pyrsistent.PMap
        """
        raise NotImplementedError

    def copy(self, **kwargs):
        """Create a copy of this filter with update configuration parameters

        :param kwargs:
            A number of key/value pairs that should be changed on the newly
            created instance of this filter.
        :type kwargs: dict
        """
        return type(self)(self.config.update(kwargs))

    def as_profile(self, author=None, description=None, example_data_url=None):
        """Treat this filter object as a profile by adding the necessary metadata

        :return: A profile instance
        :rtype: adaptivefiltering.filter.Profile
        """
        return self.as_pipeline().as_profile(
            author=author, description=description, example_data_url=example_data_url
        )

    def as_pipeline(self):
        """Convert to a filter pipeline with one stage"""
        return Pipeline([self])

    def __add__(self, other):
        """Adding filters composes a pipeline"""
        return self.as_pipeline() + other

    def __iadd__(self, other):
        raise FilterError("Cannot add filters in place. Use operator + instead")

    def widget_form(self):
        return WidgetForm(self.schema)


class Pipeline(Filter, identifier="pipeline"):
    def __init__(self, filters=[]):
        """A filter pipeline consisting of several steps

        :param filters:
            The filter steps in this pipeline. Each filter is expected to be an instance
            of :class:`~adapativefiltering.filter.Filter`.
        :type filters: list
        """
        self._filters = filters

    @property
    def filters(self):
        """The filter stages in this pipeline"""
        return self._filters

    def copy(self):
        """Create a copy of this pipeline"""
        return Pipeline(filters=self.filters)

    def as_profile(self, author=None, description=None, example_data_url=None):
        return Profile(
            filters=self.filters,
            author=author,
            description=description,
            example_data_url=example_data_url,
        )

    def as_pipeline(self):
        return self

    def __add__(self, other):
        return type(self)(filters=self.filters + other.as_pipeline().filters)

    def __iadd__(self, other):
        return Pipeline(filters=self.filters + other.as_pipeline().filters)


class Profile(Pipeline, identifier="profile"):
    def __init__(self, author=None, description=None, example_data_url=None, **kwargs):
        """A filter pipeline with additional metadata to share with other users

        :param author:
            The author of this profile.
        :type author: str
        :param description:
            A description of the usage scenarios for this profile.
        :type description: str
        :param example_data_url:
            A link to a data set that this profile excels at filtering.
        :type example_data_url: str
        """
        super(Profile, self).__init__(**kwargs)
        self._author = author
        self._description = description
        self._example_data_url = example_data_url

    @property
    def author(self):
        """The author of this profile"""
        return self._author

    @property
    def description(self):
        """A description of the usage scenarios for this profile."""
        return self._description

    @property
    def example_data_url(self):
        """A link to a data set that this profile excels at filtering."""
        return self._example_data_url
