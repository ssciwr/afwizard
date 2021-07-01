from IPython.display import display

import ipywidgets
import jsonschema
import json
import os


class WidgetFormError(Exception):
    pass


class WidgetForm:
    def __init__(self, schema, on_change=None):
        """Create a form with Jupyter widgets from a JSON schema

        :param schema:
            The JSON schema for the data object that the form should generate.
            The schema is expected to conform to the Draft 07 JSON schema standard.
            We do *not* implement the full standard, but incrementally add the
            functionality that we need.
        :type schema: dict
        :param on_change:
            This parameter accepts a callable that will be called whenever
            the widget state of one of the form widgets is changed. The callable
            (currently) accepts no parameters and its return value is ignored.
        """
        # Make sure that the given schema is valid
        filename = os.path.join(
            os.path.split(jsonschema.__file__)[0], "schemas", "draft7.json"
        )
        with open(filename, "r") as f:
            meta_schema = json.load(f)
        meta_schema["additionalProperties"] = False
        jsonschema.validate(instance=schema, schema=meta_schema)

        # Store the given data members
        self.on_change = on_change
        self.schema = schema

        # Construct the widgets
        self._construction_stack = []
        self._handlers = []
        self.widget_list = self._construct(schema)

    def show(self):
        """Show the resulting combined widget in the Jupyter notebook"""
        w = ipywidgets.VBox(self.widget_list)
        display(w)

    def data(self):
        """Get a (non-updating) snapshot of the current form data

        :returns:
            A dictionary that reflects the current state of the widget and
            conforms to the given schema.
        """
        # Construct the data by calling all the data handlers on an empty dictionary
        data = {}
        for handler in self._handlers:
            handler(data)

        # Validate the resulting document just to be sure
        jsonschema.validate(instance=data, schema=self.schema)

        return data

    def _update_function(self, widget):
        props = tuple(self._construction_stack)

        def __update_function(data):
            _data = data
            for prop in props[:-1]:
                _data = data.setdefault(prop, {})
            _data[props[-1]] = widget.value

        return __update_function

    def _construct(self, schema):
        # Enumerations are handled a dropdowns
        if "enum" in schema:
            return self._construct_enum(schema)

        # Handle other input based on the input type
        type_ = schema.get("type", None)
        if type_ is None:
            raise WidgetFormError("Expecting type information for non-enum properties")
        if not isinstance(type_, str):
            raise WidgetFormError("Not accepting arrays of types currently")
        return getattr(self, f"_construct_{type_}")(schema)

    def _construct_object(self, schema):
        widget_list = []
        for prop, subschema in schema["properties"].items():
            self._construction_stack.append(prop)
            widget_list.extend(self._construct(subschema))
            self._construction_stack.pop()

        # If this is not the root document, we wrap this in an Accordion widget
        if len(self._construction_stack):
            label = schema.get("title", self._construction_stack[-1])
            accordion = ipywidgets.Accordion(children=[ipywidgets.VBox(widget_list)])
            accordion.set_title(0, label)
            widget_list = [accordion]

        return widget_list

    def _construct_simple(self, schema, widget):
        # Construct the label widget that describes the input
        label = schema.get("title", self._construction_stack[-1])
        label = ipywidgets.Label(label)

        # Apply a potential default
        if "default" in schema:
            widget.value = schema["default"]

        # Apply potential constant values
        if "const" in schema:
            widget.value = schema["const"]
            widget.disabled = True

        def _fire_on_change(change):
            if self.on_change:
                self.on_change()

        widget.observe(_fire_on_change)
        self._handlers.append(self._update_function(widget))
        return [ipywidgets.Box([label, widget])]

    def _construct_string(self, schema):
        return self._construct_simple(schema, ipywidgets.Text())

    def _construct_number(self, schema):
        return self._construct_simple(schema, ipywidgets.FloatText())

    def _construct_boolean(self, schema):
        return self._construct_simple(schema, ipywidgets.Checkbox())

    def _construct_null(self, schema):
        prop = self._construction_stack[-1]

        def _add_none(data):
            data[prop] = None

        self._handlers.append(_add_none)
        return []

    def _construct_array(self, schema):
        raise NotImplementedError("array not yet implemented")

    def _construct_enum(self, schema):
        return self._construct_simple(
            schema, ipywidgets.Dropdown(options=schema["enum"])
        )
