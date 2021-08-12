from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import AdaptiveFilteringError
from adaptivefiltering.widgets import WidgetForm

import json
import jsonschema
import os
import pyrsistent


class FilterError(AdaptiveFilteringError):
    pass


class Filter:
    def __init__(self, **config):
        """The base class for a filter in adaptivefiltering

        A filter can either be constructed from a configuration or be deserialized
        from a file using the :func:`~adaptivefiltering.load_filter` function.

        :param config:
            The dictionary of configuration values that conforms to the schema
            defined by the schema property.
        :type config: dict
        """
        self.config = config

    # Store a registry of filter implementations derived from this base class
    _filter_impls = {}
    _filter_is_backend = {}

    def __init_subclass__(cls, identifier=None, backend=True):
        """Register all filter implementations that subclass this base class

        :param identifier:
            A name that identifies this subclass
        :type identifier: str
        :param backend:
            Whether this class defines a new filtering backend. Meta filters like
            pipelines, profiles etc. should set this to False.
        """
        if identifier is None:
            raise FilterError("Please specify identifier when inheriting from filter")
        if identifier in Filter._filter_impls:
            raise FilterError(f"Filter identifier {identifier} already taken")
        Filter._filter_impls[identifier] = cls
        Filter._filter_is_backend[identifier] = backend
        cls._identifier = identifier

    @property
    def config(self):
        """The configuration dictionary for this filter

        :type: pyrsistent.PMap
        """
        return self._config

    @config.setter
    def config(self, _config):
        _config = pyrsistent.freeze(_config)
        jsonschema.validate(
            instance=pyrsistent.thaw(_config), schema=pyrsistent.thaw(self.schema())
        )
        self._config = _config

    def execute(self, dataset):
        """Apply the filter to a given data set

        This method needs to be implemented by all filter backends. It is expected
        to return a new data set instance that contains the filter result and have
        no side effects on the input data set. It also needs to record the data provenance
        on the newly created data set.

        :param dataset:
            The data set to apply the filter to.
        :type dataset: adaptivefiltering.DataSet
        :return:
            A modified data set instance with the filter applied.
        """
        raise NotImplementedError  # pragma: no cover

    def _serialize(self):
        """Serialize this filter.

        Serialize this object into a (nested) built-in data structure. Passing
        the result to :func:`~adaptivefiltering.filter.Filter._deserialize` should
        reconstruct the object. Note that this method is an implementation detail
        of a given filter implementation: To serialize a given filter, use
        :func:`~adaptivefiltering.filter.serialize` instead.

        :return:
            The data structure after serialization.
        """
        return pyrsistent.thaw(self.config)

    @classmethod
    def _deserialize(cls, data):
        """Deserialize this filter.

        Deserialize this objecte from a (nested) built-in data structure. This is
        the counterpart of :func:`~adaptivefiltering.filter.Filter._serialize`.
        Note that this method is an implementation detail
        of a given filter implementation: To serialize a given filter, use
        :func:`~adaptivefiltering.filter.serialize` instead.

        :param data:
            The data string from which to deserialize the filter.
        :return:
            The deserialized filter instance
        """
        return cls(**data)

    @classmethod
    def schema(cls):
        """Define the configuration schema for this filter

        :return:
            A nested dictionary data structure that contains the JSON schema
            for the configuration of this filter. The schema should conform to
            the Draft 7 JSON Schema standard (https://json-schema.org/).
        :rtype: pyrsistent.PMap
        """
        return pyrsistent.m(type="object")

    @classmethod
    def form_schema(cls):
        """Define the part of the configuration schema that should be exposed to the user

        Backend's inheriting from the :class:`~adaptivefiltering.filter.Filter` interface class can use that to
        implicitly handle some parameters. These would still be part of the
        schema, but they are automatically added in the :func:`~adaptivefiltering.filter.Filter.execute` part.
        """
        return cls.schema()

    def copy(self, **kwargs):
        """Create a copy of this filter with updated configuration parameters

        :param kwargs:
            A number of key/value pairs that should be changed on the newly
            created instance of this filter.
        :type kwargs: dict
        """
        return type(self)(**self.config.update(kwargs))

    def as_pipeline(self):
        """Convert to a filter pipeline with one stage"""
        return Pipeline(filters=[self])

    def widget_form(self):
        """Create a widget form for this filter

        :return: The widget form
        :rtype: :class:`~adaptivefiltering.widgets.WidgetForm`
        """
        form = WidgetForm(self.form_schema())
        form.data = self.config
        return form

    def __add__(self, other):
        """Adding filters composes a pipeline"""
        return self.as_pipeline() + other

    def __iadd__(self, other):
        raise FilterError("Cannot add filters in place. Use operator + instead")

    def __repr__(self):
        return f"{type(self).__name__}(**{{{repr(self.config)}}})"

    def __eq__(self, other):
        return repr(self) == repr(other)

    @classmethod
    def enabled(cls):
        return True


# Register the base class itself
Filter._filter_impls["base"] = Filter
Filter._filter_is_backend["base"] = False
Filter._identifier = "base"


class PipelineMixin:
    def __init__(self, **kwargs):
        """A filter pipeline consisting of several steps

        :param filters:
            The filter steps in this pipeline. Each filter is expected to be an instance
            of :class:`~adapativefiltering.filter.Filter`.
        :type filters: list
        """
        self.config = kwargs

    @classmethod
    def schema(cls):
        return pyrsistent.freeze(load_schema("pipeline.json"))

    def as_pipeline(self):
        return self

    def __add__(self, other):
        return type(self)(
            filters=self.config["filters"] + other.as_pipeline().config["filters"]
        )

    def __iadd__(self, other):
        return self.copy(
            filters=self.config["filters"] + other.as_pipeline().config["filters"]
        )

    def widget_form(self):
        # Collect the list of available backend implementations
        backends = []
        for ident, class_ in Filter._filter_impls.items():
            if Filter._filter_is_backend[ident]:
                if class_.enabled():
                    backends.append(class_.form_schema())

        # Construct a widget that let's you select the backend
        schema = pyrsistent.thaw(self.schema())
        schema["properties"]["filters"] = {
            "type": "array",
            "items": {"oneOf": backends, "title": "Filtering Backend"},
        }

        form = WidgetForm(pyrsistent.freeze(schema))
        form.data = self.config
        return form

    def _serialize(self):
        data = pyrsistent.thaw(self.config)
        data["filters"] = [serialize_filter(f) for f in self.config["filters"]]
        return data

    @classmethod
    def _deserialize(cls, data):
        data["filters"] = [deserialize_filter(f) for f in data["filters"]]
        return cls(**data)

    @property
    def author(self):
        """The author of this profile"""
        return self.config["metadata"]["author"]

    @property
    def description(self):
        """A description of the usage scenarios for this profile."""
        return self.config["metadata"]["description"]

    @property
    def example_data_url(self):
        """A link to a data set that this profile excels at filtering."""
        return self.config["metadata"]["example_data_url"]


class Pipeline(PipelineMixin, Filter, identifier="pipeline", backend=False):
    def execute(self, dataset):
        for f in self.config["filters"]:
            dataset = f.execute(dataset)
        return dataset


def serialize_filter(filter_):
    """Serialize a given filter.

    This relies on :func:`~adaptivefilter.filter.Filter._serialize` to do the
    object serialization, but adds information about the correct filter type.
    """
    assert isinstance(filter_, Filter)

    # Construct a dictionary with filter type and data
    data = {}
    data["filter_type"] = type(filter_)._identifier
    data["filter_data"] = filter_._serialize()
    return data


def deserialize_filter(data):
    """Deserialize a filter.

    This relies on :func:`~adaptivefilter.filter.Filter._deserialize` to do the
    object deserialization, but reads the type information to select the correct
    filter class to construct.
    """
    # Validate the data against our filter meta schema
    schema = load_schema("filter.json")
    jsonschema.validate(instance=data, schema=schema)

    # Find the correct type and do the deserialization
    type_ = Filter._filter_impls[data["filter_type"]]
    return type_._deserialize(data["filter_data"])


def save_filter(filter_, filename):
    """Save a filter to a file

    Filters saved to disk with this function can be reconstructed with the
    :func:`~adaptivefiltering.load_filter` method.

    :param filter_:
        The filter object to write to disk
    :type filter_: Filter
    :param filename:
        The filename where to write the filter. Relative paths are interpreted
        w.r.t. the current working directory.
    """
    filename = os.path.abspath(filename)
    with open(filename, "w") as f:
        json.dump(serialize_filter(filter_), f)


def load_filter(filename):
    """Load a filter from a file

    This function restores filters that were previously saved to disk using the
    :func:`~adaptivefiltering.save_filter` function.

    :param filename:
        The filename to load the filter from. Relative paths are interpreted
        w.r.t. the current working directory.
    :type filename: str
    """
    filename = os.path.abspath(filename)
    with open(filename, "r") as f:
        return deserialize_filter(json.load(f))
