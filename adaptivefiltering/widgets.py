from IPython.display import display

import ipywidgets
import jsonschema
import json
import os
import pyrsistent


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
        self._data_creator, self.widget_list = self._construct(schema)

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
        data = self._data_creator()

        # Validate the resulting document just to be sure
        jsonschema.validate(instance=pyrsistent.thaw(data), schema=self.schema)

        return data

    def _construct(self, schema, label=True):
        # Enumerations are handled a dropdowns
        if "enum" in schema:
            return self._construct_enum(schema, label=label)

        # Handle other input based on the input type
        type_ = schema.get("type", None)
        if type_ is None:
            raise WidgetFormError("Expecting type information for non-enum properties")
        if not isinstance(type_, str):
            raise WidgetFormError("Not accepting arrays of types currently")
        return getattr(self, f"_construct_{type_}")(schema, label=label)

    def _construct_object(self, schema, label=True):
        update_list = []
        widget_list = []
        for prop, subschema in schema["properties"].items():
            self._construction_stack.append(prop)
            u, w = self._construct(subschema, label=label)
            update_list.append((prop, u))
            widget_list.extend(w)
            self._construction_stack.pop()

        # If this is not the root document, we wrap this in an Accordion widget
        if len(self._construction_stack):
            accordion = ipywidgets.Accordion(children=[ipywidgets.VBox(widget_list)])
            if label:
                accordion.set_title(
                    0, schema.get("title", self._construction_stack[-1])
                )
            widget_list = [accordion]

        return lambda: pyrsistent.m(**{p: f() for p, f in update_list}), widget_list

    def _construct_simple(self, schema, widget, label=True):
        # Construct the label widget that describes the input
        box = [widget]
        if label:
            box.insert(
                0, ipywidgets.Label(schema.get("title", self._construction_stack[-1]))
            )

        # Apply a potential default
        if "default" in schema:
            widget.value = schema["default"]

        # Apply potential constant values
        if "const" in schema:
            widget.value = schema["const"]
            widget.disabled = True

        # Register a change handler that triggers the forms change handler
        def _fire_on_change(change):
            if self.on_change:
                self.on_change()

        widget.observe(_fire_on_change)

        # self._handlers.append(self._update_function(widget))
        return lambda: widget.value, [ipywidgets.Box(box)]

    def _construct_string(self, schema, label=True):
        return self._construct_simple(schema, ipywidgets.Text(), label=label)

    def _construct_number(self, schema, label=True):
        return self._construct_simple(schema, ipywidgets.FloatText(), label=label)

    def _construct_boolean(self, schema, label=True):
        return self._construct_simple(schema, ipywidgets.Checkbox(), label=label)

    def _construct_null(self, schema, label=True):
        return lambda: None, []

    def _construct_array(self, schema, label=True):
        if "items" not in schema:
            raise WidgetFormError("Expecting 'items' key for 'array' type")

        # Construct a widget that allows to add an array entry
        button = ipywidgets.Button(description="Add entry", icon="plus")
        vbox = ipywidgets.VBox([button])

        def add_entry(_):
            item = self._construct(schema["items"], label=False)[1][0]
            trash = ipywidgets.Button(icon="trash")
            up = ipywidgets.Button(icon="arrow-up")
            down = ipywidgets.Button(icon="arrow-down")

            def remove_entry(b):
                vbox.children = tuple(
                    c for c in vbox.children[:-1] if b not in c.children
                ) + (vbox.children[-1],)

            trash.on_click(remove_entry)

            def move(dir):
                def _move(b):
                    items = list(vbox.children[:-1])
                    for i, it in enumerate(items):
                        if b in it.children:
                            newi = min(max(i + dir, 0), len(items) - 1)
                            items[i], items[newi] = items[newi], items[i]
                            break

                    vbox.children = tuple(items) + (vbox.children[-1],)

                return _move

            # Register the handler for moving up and down
            up.on_click(move(-1))
            down.on_click(move(1))

            vbox.children = (ipywidgets.HBox([item, trash, up, down]),) + vbox.children

        button.on_click(add_entry)

        # TODO: I know this is not fit for non-scalar list entries, but we might need
        #       a bit of refactoring to target the more general use case
        return lambda: pyrsistent.pvector(
            i.children[0].children[0].value for i in vbox.children[:-1]
        ), [vbox]

    def _construct_enum(self, schema, label=True):
        return self._construct_simple(
            schema, ipywidgets.Dropdown(options=schema["enum"]), label=label
        )
