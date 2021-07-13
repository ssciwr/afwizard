from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import AdaptiveFilteringError

from IPython.display import display

import ipywidgets
import jsonschema
import json
import os
import pyrsistent


class WidgetFormError(AdaptiveFilteringError):
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
        jsonschema.validate(instance=pyrsistent.thaw(schema), schema=meta_schema)

        # Store the given data members
        self.on_change = on_change
        self.schema = schema

        # Construct the widgets
        self._data_creator, self.widget_list = self._construct(
            schema, root=True, label=None
        )

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
        jsonschema.validate(
            instance=pyrsistent.thaw(data), schema=pyrsistent.thaw(self.schema)
        )

        return data

    def _construct(self, schema, label=None, root=False):
        # If this references another schema, we jump into that schema
        if "$ref" in schema:
            return self._construct(load_schema(schema["$ref"]), label=label, root=root)

        # Enumerations are handled a dropdowns
        if "enum" in schema:
            return self._construct_enum(schema, label=label)

        # anyOf rules are handled with dropdown selections
        if "anyOf" in schema:
            return self._construct_anyof(schema, label=label)

        # We use the same code for oneOf and allOf - if the data cannot be validated,
        # a validation error will be thrown when accessing the data. There is no
        # upfront checking in the form.
        if "oneOf" in schema:
            return self._construct_anyof(schema, label=label, key="oneOf")
        if "allOf" in schema:
            return self._construct_anyof(schema, label=label, key="allOf")

        # Handle other input based on the input type
        type_ = schema.get("type", None)
        if type_ is None:
            raise WidgetFormError("Expecting type information for non-enum properties")
        if not isinstance(type_, str):
            raise WidgetFormError("Not accepting arrays of types currently")
        return getattr(self, f"_construct_{type_}")(schema, label=label, root=root)

    def _wrap_accordion(self, widget_list, schema, label=None):
        accordion = ipywidgets.Accordion(children=[ipywidgets.VBox(widget_list)])
        if label is not None or "title" in schema:
            accordion.set_title(0, schema.get("title", label))
        return [accordion]

    def _construct_object(self, schema, label=None, root=False):
        update_list = []
        widget_list = []
        for prop, subschema in schema["properties"].items():
            u, w = self._construct(subschema, label=prop)
            update_list.append((prop, u))
            widget_list.extend(w)

        # If this is not the root document, we wrap this in an Accordion widget
        if not root:
            widget_list = self._wrap_accordion(widget_list, schema, label=label)

        return lambda: pyrsistent.m(**{p: f() for p, f in update_list}), widget_list

    def _construct_simple(self, schema, widget, label=None, root=False):
        # Construct the label widget that describes the input
        box = [widget]
        if label is not None or "title" in schema:
            box.insert(0, ipywidgets.Label(schema.get("title", label)))

        # Apply a potential default
        if "default" in schema:
            widget.value = schema["default"]

        # Apply potential constant values without generating a widget
        if "const" in schema:
            return lambda: schema["const"], []

        # Register a change handler that triggers the forms change handler
        def _fire_on_change(change):
            if self.on_change:
                self.on_change()

        widget.observe(_fire_on_change)

        return lambda: widget.value, [ipywidgets.Box(box)]

    def _construct_string(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.Text(), label=label)

    def _construct_number(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.FloatText(), label=label)

    def _construct_integer(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.IntText(), label=label)

    def _construct_boolean(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.Checkbox(), label=label)

    def _construct_null(self, schema, label=None, root=False):
        return lambda: None, []

    def _construct_array(self, schema, label=None, root=False):
        if "items" not in schema:
            raise WidgetFormError("Expecting 'items' key for 'array' type")

        # Construct a widget that allows to add an array entry
        button = ipywidgets.Button(description="Add entry", icon="plus")
        vbox = ipywidgets.VBox([button])
        data_handlers = []

        def add_entry(_):
            # if we are at the specified maximum, add should be ignored
            if "maxItems" in schema:
                if len(vbox.children) == schema["maxItems"]:
                    return

            handler, item = self._construct(schema["items"], label=None)
            data_handlers.insert(0, handler)
            item = item[0]
            trash = ipywidgets.Button(icon="trash")
            up = ipywidgets.Button(icon="arrow-up")
            down = ipywidgets.Button(icon="arrow-down")

            def remove_entry(b):
                # If we are at the specified minimum, remove should be ignored
                if "minItems" in schema:
                    if len(vbox.children) == schema["minItems"]:
                        return

                # Identify the current list index of the entry
                for index, child in enumerate(vbox.children):
                    if b in child.children:
                        break

                # Remove it from the widget list and the handler list
                vbox.children = vbox.children[:index] + vbox.children[index + 1 :]
                data_handlers.pop(index)

            trash.on_click(remove_entry)

            def move(dir):
                def _move(b):
                    items = list(vbox.children[:-1])
                    for i, it in enumerate(items):
                        if b in it.children:
                            newi = min(max(i + dir, 0), len(items) - 1)
                            items[i], items[newi] = items[newi], items[i]
                            data_handlers[i], data_handlers[newi] = (
                                data_handlers[newi],
                                data_handlers[i],
                            )
                            break

                    vbox.children = tuple(items) + (vbox.children[-1],)

                return _move

            # Register the handler for moving up and down
            up.on_click(move(-1))
            down.on_click(move(1))

            vbox.children = (ipywidgets.HBox([item, trash, up, down]),) + vbox.children

        button.on_click(add_entry)

        # Initialize the widget with the minimal number of subwidgets
        for _ in range(schema.get("minItems", 0)):
            add_entry(_)

        # If this is not the root document, we wrap this in an Accordion widget
        wrapped_vbox = [vbox]
        if not root:
            wrapped_vbox = self._wrap_accordion(wrapped_vbox, schema, label=label)

        return lambda: pyrsistent.pvector(h() for h in data_handlers), wrapped_vbox

    def _construct_enum(self, schema, label=None, root=False):
        # We omit trivial enums, but make sure that they end up in the result
        if len(schema["enum"]) == 1:
            return lambda: schema["enum"][0], []

        # Otherwise, we use a dropdown menu
        return self._construct_simple(
            schema, ipywidgets.Dropdown(options=schema["enum"]), label=label
        )

    def _construct_anyof(self, schema, label=None, key="anyOf"):
        names = []
        handlers = []
        subwidgets = []

        # Iterate over the given subschema
        for s in schema[key]:
            if "title" in s:
                names.append(s["title"])
                handler, widget = self._construct(s)
                handlers.append(handler)
                subwidgets.append(widget)
            else:
                raise WidgetFormError(
                    "Schemas within anyOf/oneOf/allOf need to set the title field"
                )

        # Create the selector and subschema widget
        selector = ipywidgets.Dropdown(options=names, value=names[0])
        widget = ipywidgets.VBox([selector] + subwidgets[0])

        # Whenever there is a change, we switch the subschema widget
        def _select(change):
            widget.children = [selector] + subwidgets[names.index(selector.value)]

        selector.observe(_select)

        return lambda: handlers[names.index(selector.value)](), [widget]
