from afwizard.paths import load_schema, check_file_extension
from afwizard.utils import AFwizardError, as_number_type
from afwizard.versioning import (
    AFWIZARD_DATAMODEL_MAJOR_VERSION,
    AFWIZARD_DATAMODEL_MINOR_VERSION,
    upgrade_filter,
)
from afwizard.widgets import BatchDataWidgetForm

import json
import jsonmerge
import jsonschema
import os
import pyrsistent


class FilterError(AFwizardError):
    pass


class Filter:
    def __init__(self, _variability=[], **config):
        """The base class for a filter in AFwizard

        A filter can either be constructed from a configuration or be deserialized
        from a file using the :func:`~afwizard.load_filter` function.

        :param config:
            The dictionary of configuration values that conforms to the schema
            defined by the schema property.
        :type config: dict
        """
        self.config = config
        self.variability = _variability

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
        """Change the filter configuration

        Performs automatic validation against the filter's schema.
        """
        # Assert that the given backend matches our backend class.
        if "_backend" in _config:
            assert _config["_backend"] == self._identifier

        # Validate the given configuration
        _config = pyrsistent.freeze(_config)
        jsonschema.validate(
            instance=pyrsistent.thaw(_config), schema=pyrsistent.thaw(self.schema())
        )

        # Store the validated config
        self._config = _config

    @property
    def variability(self):
        """Access the filter's end user configuration variability"""
        return self._variability

    @variability.setter
    def variability(self, _variability):
        """Change the filter's end user configuration variability"""
        # Validate the variability input
        _variability = pyrsistent.thaw(_variability)
        schema = load_schema("variability.json")
        jsonschema.validate(instance=_variability, schema=schema)

        # Filter for persistent variation only
        var = [v for v in _variability if v["persist"]]
        self._variability = pyrsistent.freeze(var)

    @property
    def variability_schema(self):
        """Create a schema for the variability of this filter"""

        # Access regular filter configuration to get the default value
        def access_data(data, path=[]):
            if len(path) == 0:
                return data

            pathitem = path[-1]
            if "key" in pathitem:
                return access_data(data[pathitem["key"]], path=path[:-1])
            if "index" in pathitem:
                return access_data(data[pathitem["index"]], path=path[:-1])

        # Create a dictionary schema
        schema = {"type": "object", "properties": {}}

        # Iterate over given variation points
        for var in self._variability:
            if "name" not in var:
                raise AFwizardError(
                    f"Name argument is required for variability definition"
                )

            # Create a subschema for this variation
            varschema = {
                "type": var["type"],
                "title": var["name"],
                "description": var["description"],
            }

            # Analyse values
            if varschema["type"] == "string":
                varschema["enum"] = [v.strip() for v in var["values"].split(",")]
            elif varschema["type"] in ("integer", "number"):
                splitted = var["values"].split(",")
                # This is a discrete variation
                if len(splitted) > 1:
                    varschema["enum"] = [
                        as_number_type(varschema["type"], v.strip())
                        for v in var["values"].split(",")
                    ]
                else:
                    slice_ = var["values"].split(":")
                    if len(slice_) == 1:
                        varschema["enum"] = [
                            as_number_type(varschema["type"], splitted[0].strip())
                        ]
                    elif len(slice_) == 2:
                        varschema["minimum"] = as_number_type(
                            varschema["type"], slice_[0]
                        )
                        varschema["maximum"] = as_number_type(
                            varschema["type"], slice_[1]
                        )
                    elif len(slice_) == 3:
                        options = []
                        current = as_number_type(varschema["type"], slice_[0])
                        while current <= as_number_type(varschema["type"], slice_[1]):
                            options.append(current)
                            current = current + as_number_type(
                                varschema["type"], slice_[2]
                            )
                        varschema["enum"] = options
                    else:
                        raise AFwizardError(
                            f"Variability string '{splitted[0]}' not understood!"
                        )
            else:
                raise NotImplementedError(
                    f"Variability for type {var['type']} not implemented."
                )

            # Add default by accessing actual configuration
            varschema["default"] = access_data(self.config, path=var["path"])

            # Merge the subschema into the bigger object schema
            schema["properties"][var["name"].lower()] = varschema

        return schema

    def execute(self, dataset, **variability_data):
        """Apply the filter to a given data set

        This method needs to be implemented by all filter backends. It is expected
        to return a new data set instance that contains the filter result and have
        no side effects on the input data set.

        :param dataset:
            The data set to apply the filter to.
        :type dataset: afwizard.DataSet
        :param variability_data:
            Configuration values for the variation points of this filter.
        :return:
            A modified data set instance with the filter applied.
        """
        raise NotImplementedError  # pragma: no cover

    def execute_interactive(self, dataset):
        """Apply the filter in an interactive setting

        Using this methods allows you to explore the finetuning capabilities
        of the filter (if it provides any).

        :param dataset:
            The data set to apply the filter to.
        :type dataset: afwizard.DataSet
        :returns:
            A filter pipeline copy with the fine tuning configuration baked in.
        """

        from afwizard.apps import execute_interactive

        return execute_interactive(dataset, self)

    def _serialize(self):
        """Serialize this filter.

        Serialize this object into a (nested) built-in data structure. Passing
        the result to :func:`~afwizard.filter.Filter._deserialize` should
        reconstruct the object. Note that this method is an implementation detail
        of a given filter implementation: To serialize a given filter, use
        :func:`~afwizard.filter.serialize` instead.

        :return:
            The data structure after serialization.
        """
        data = pyrsistent.thaw(self.config)
        data["_backend"] = self._identifier
        data["_variability"] = pyrsistent.thaw(self._variability)
        return data

    @classmethod
    def _deserialize(cls, data):
        """Deserialize this filter.

        Deserialize this objecte from a (nested) built-in data structure. This is
        the counterpart of :func:`~afwizard.filter.Filter._serialize`.
        Note that this method is an implementation detail
        of a given filter implementation: To serialize a given filter, use
        :func:`~afwizard.filter.serialize` instead.

        :param data:
            The data string from which to deserialize the filter.
        :return:
            The deserialized filter instance
        """
        assert cls._identifier == data.pop("_backend")
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

        Backend's inheriting from the :class:`~afwizard.filter.Filter` interface class can use that to
        implicitly handle some parameters. These would still be part of the
        schema, but they are automatically added in the :func:`~afwizard.filter.Filter.execute` part.
        """
        return cls.schema()

    def copy(self, **kwargs):
        """Create a copy of this filter with updated configuration parameters

        :param kwargs:
            A number of key/value pairs that should be changed on the newly
            created instance of this filter.
        :type kwargs: dict
        """
        kwargs.setdefault("_variability", self._variability)
        return type(self)(**self.config.update(kwargs))

    def as_pipeline(self):
        """Convert to a filter pipeline with one stage"""
        return Pipeline(filters=[self])

    def widget_form(self):
        """Create a widget form for this filter

        :return: The widget form
        :rtype: :class:`~afwizard.widgets.BatchDataWidgetForm`
        """
        form = BatchDataWidgetForm(
            pyrsistent.thaw(self.form_schema()),
            vertically_place_labels=True,
            preconstruct_array_items=1,
            nobatch_keys=["metadata"],
        )
        form.data = pyrsistent.thaw(self.config)
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
        """Whether the backend is currently usable

        This allows disabling e.g. proprietary backends whenever
        the necessary proprietary code is not available.
        """
        return True

    def used_backends(self):
        """Return the identifiers of the backends used in this filter"""
        return (self._identifier,)

    def _modify_filter_config(self, variability_data):
        # Validate the given variablity data
        jsonschema.validate(
            instance=pyrsistent.thaw(variability_data), schema=self.variability_schema
        )

        # Update a copy of the configuration according to the given data
        config = self.config
        for var in self.variability:
            value = variability_data.get(var["name"].lower(), None)
            if value is not None:
                var = var.update({"values": value})
                config = update_data(config, var)

        return config


# Register the base class itself
Filter._filter_impls["base"] = Filter
Filter._filter_is_backend["base"] = False
Filter._identifier = "base"


class PipelineMixin:
    def __init__(self, _variability=[], **kwargs):
        """A filter pipeline consisting of several steps

        :param filters:
            The filter steps in this pipeline. Each filter is expected to be an instance
            of :class:`~adapativefiltering.filter.Filter`.
        :type filters: list
        """
        filters = []
        for f in kwargs.get("filters", []):
            if isinstance(f, Filter):
                filters.append(f.config)
            else:
                filters.append(f)
        kwargs["filters"] = filters

        self.config = kwargs
        self.variability = _variability

    @classmethod
    def _schema_impl(cls, method):
        # Load the schema with pipeline metadata
        pipeline_schema = load_schema("pipeline.json")

        # Extract all the backend schema
        backend_schemas = []
        for ident, class_ in Filter._filter_impls.items():
            if Filter._filter_is_backend[ident]:
                if class_.enabled():
                    bschema = getattr(class_, method)()
                    backend_schemas.append(pyrsistent.thaw(bschema))

        # Merge the backend schemas into a single one
        merge_schema = {"properties": {"anyOf": {"mergeStrategy": "append"}}}
        merger = jsonmerge.Merger(merge_schema)
        merged = backend_schemas[0]
        for other in backend_schemas[1:]:
            merged = merger.merge(merged, other)

        # Insert the merged schema into the pipeline schema
        pipeline_schema["properties"]["filters"]["items"] = merged

        return pyrsistent.freeze(pipeline_schema)

    @classmethod
    def schema(cls):
        return cls._schema_impl("schema")

    @classmethod
    def form_schema(cls):
        return cls._schema_impl("form_schema")

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

    def used_backends(self):
        return tuple(set(f["_backend"] for f in self.config["filters"]))

    @property
    def author(self):
        """The author of this profile"""
        return self.config.get("metadata", {}).get("author", "")

    @property
    def description(self):
        """A description of the usage scenarios for this profile."""
        return self.config.get("metadata", {}).get("description", "")

    @property
    def example_data_url(self):
        """A link to a data set that this profile excels at filtering."""
        return self.config.get("metadata", {}).get("example_data_url", "")

    @property
    def title(self):
        """A telling display name for the filter pipeline"""
        return self.config.get("metadata", {}).get("title", "")

    @property
    def keywords(self):
        """The keywords that describe this filter pipeline"""
        return self.config.get("metadata", {}).get("keywords", ())


class Pipeline(PipelineMixin, Filter, identifier="pipeline", backend=False):
    def execute(self, dataset, **variability_data):
        # Apply variabilility without changing self
        config = self._modify_filter_config(variability_data)

        for f in config["filters"]:
            data = pyrsistent.thaw(f)
            data["_major"] = AFWIZARD_DATAMODEL_MAJOR_VERSION
            data["_minor"] = AFWIZARD_DATAMODEL_MINOR_VERSION
            fobj = deserialize_filter(data)
            dataset = fobj.execute(dataset)

        return dataset


def serialize_filter(filter_):
    """Serialize a given filter.

    This relies on :func:`~adaptivefilter.filter.Filter._serialize` to do the
    object serialization, but adds information about the correct filter type.
    """
    data = filter_._serialize()
    data["_backend"] = filter_._identifier
    data["_major"] = AFWIZARD_DATAMODEL_MAJOR_VERSION
    data["_minor"] = AFWIZARD_DATAMODEL_MINOR_VERSION
    return data


def deserialize_filter(data):
    """Deserialize a filter.

    This relies on :func:`~adaptivefilter.filter.Filter._deserialize` to do the
    object deserialization, but reads the type information to select the correct
    filter class to construct.
    """
    # Find the correct type and do the deserialization
    type_ = Filter._filter_impls[data["_backend"]]
    data = upgrade_filter(data)
    data.pop("_major")
    data.pop("_minor")
    return type_._deserialize(data)


def save_filter(filter_, filename):
    """Save a filter to a file

    Filters saved to disk with this function can be reconstructed with the
    :func:`~afwizard.load_filter` method.

    :param filter_:
        The filter object to write to disk
    :type filter_: Filter
    :param filename:
        The filename where to write the filter. Relative paths are interpreted
        w.r.t. the current working directory.
    """
    filename = check_file_extension(filename, [".json"], ".json")

    # If the filename is not already absolute, we maybe preprend the path
    # of the current filter library
    if not os.path.isabs(filename):
        from afwizard.library import get_current_filter_library

        lib = get_current_filter_library()
        if lib is None:
            filename = os.path.abspath(filename)
        else:
            filename = os.path.join(lib, filename)

    # If the filter has insufficient metadata we give a warning
    if isinstance(filter_, PipelineMixin):
        if filter_.title == "" or filter_.author == "" or len(filter_.keywords) == 0:
            print(
                "WARNING: This filter has insufficient metadata. Please consider adding in af.pipeline_tuning!"
            )

    with open(filename, "w") as f:
        json.dump(serialize_filter(filter_), f)


def load_filter(filename):
    """Load a filter from a file

    This function restores filters that were previously saved to disk using the
    :func:`~afwizard.save_filter` function.

    :param filename:
        The filename to load the filter from. Relative paths are interpreted
        w.r.t. the current working directory.
    :type filename: str
    """
    # Find the file across all libraries
    from afwizard.library import locate_filter

    filename = locate_filter(filename)

    with open(filename, "r") as f:
        return deserialize_filter(json.load(f))


def update_data(data, modifier):
    """Update a pyrsistent data structure according to a given modifier"""
    if len(modifier["path"]) == 0:
        return modifier["values"]

    pathitem = modifier["path"][-1]
    if "key" in pathitem:
        return data.update(
            {
                pathitem["key"]: update_data(
                    data[pathitem["key"]],
                    {"path": modifier["path"][:-1], "values": modifier["values"]},
                )
            }
        )
    if "index" in pathitem:
        l = data.tolist()
        l[pathitem["index"]] = update_data(
            l[pathitem["index"]],
            {"path": modifier["path"][:-1], "values": modifier["values"]},
        )
        return pyrsistent.pvector(l)


def modify_filter_config(config, moddata, variation):
    """Modify a filter configuration according to variability data"""
    for var in variation:
        var["values"] = moddata[var["name"].lower()]
        config = update_data(config, var)
    return config
