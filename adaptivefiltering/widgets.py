from IPython.display import display

import ipywidgets
import jsonschema


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
        jsonschema.Draft7Validator.check_schema(schema)

        # Create data members
        self.widget_list = []
        self.on_change = on_change
        self._handlers = []

        # Construct the widgets
        self._construction_stack = []
        self._construct(schema)

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
        data = {}
        for handler in self._handlers:
            handler(data)
        return data

    def _update_function(self, widget):
        prop = self._construction_stack[-1]

        def __update_function(data):
            data[prop] = widget.value

        return __update_function

    def _construct(self, schema):
        type_ = schema.get("type", None)
        if type_ is None:
            raise WidgetFormError("Expecting type information for all properties")
        if not isinstance(type_, str):
            raise WidgetFormError("Not accepting arrays of types currently")
        getattr(self, f"_construct_{type_}")(schema)

    def _construct_object(self, schema):
        for prop, subschema in schema["properties"].items():
            self._construction_stack.append(prop)
            self._construct(subschema)
            self._construction_stack.pop()

    def _construct_simple(self, schema, widgetType):
        # Construct the base widgets
        label = ipywidgets.Label(self._construction_stack[-1])
        widget = widgetType()

        # Apply a potential default
        if "default" in schema:
            widget.value = schema["default"]

        def _fire_on_change(change):
            if self.on_change:
                self.on_change()

        widget.observe(_fire_on_change)
        self.widget_list.append(ipywidgets.Box([label, widget]))
        self._handlers.append(self._update_function(widget))

    def _construct_string(self, schema):
        return self._construct_simple(schema, ipywidgets.Text)

    def _construct_number(self, schema):
        return self._construct_simple(schema, ipywidgets.FloatText)

    def _construct_array(self, schema):
        raise NotImplementedError("array not yet implemented")
