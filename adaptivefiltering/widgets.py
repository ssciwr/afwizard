from jsonschema.exceptions import ValidationError
from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import AdaptiveFilteringError

from IPython.display import display

import dataclasses
import ipywidgets
import jsonschema
import json
import os
import pyrsistent
import typing


class WidgetFormError(AdaptiveFilteringError):
    pass


@dataclasses.dataclass
class WidgetFormElement:
    getter: typing.Callable
    setter: typing.Callable
    widgets: list


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
        self._form_element = self._construct(schema, root=True, label=None)

    def show(self):
        """Show the resulting combined widget in the Jupyter notebook"""
        w = ipywidgets.VBox(self._form_element.widgets)
        display(w)

    @property
    def data(self):
        """Get a (non-updating) snapshot of the current form data

        :returns:
            A dictionary that reflects the current state of the widget and
            conforms to the given schema.
        """
        # Construct the data by calling all the data handlers on an empty dictionary
        data = self._form_element.getter()

        # Validate the resulting document just to be sure
        jsonschema.validate(
            instance=pyrsistent.thaw(data), schema=pyrsistent.thaw(self.schema)
        )

        return data

    @data.setter
    def data(self, _data):
        self._form_element.setter(_data)

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

        # This folds the accordion
        accordion.selected_index = None
        return [accordion]

    def _construct_object(self, schema, label=None, root=False):
        # Construct form elements for all the fields
        elements = {}
        for prop, subschema in schema["properties"].items():
            elements[prop] = self._construct(subschema, label=prop)

        # If this is not the root document, we wrap this in an Accordion widget
        widget_list = sum((e.widgets for e in elements.values()), [])
        if not root:
            widget_list = self._wrap_accordion(widget_list, schema, label=label)

        def _setter(_d):
            for k, v in _d.items():
                elements[k].setter(v)

        return WidgetFormElement(
            getter=lambda: pyrsistent.m(**{p: e.getter() for p, e in elements.items()}),
            setter=_setter,
            widgets=widget_list,
        )

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
            return WidgetFormElement(
                getter=lambda: schema["const"], setter=lambda _: None, widgets=[]
            )

        # Register a change handler that triggers the forms change handler
        def _fire_on_change(change):
            if self.on_change:
                self.on_change()

        widget.observe(_fire_on_change)

        def _setter(_d):
            widget.value = _d

        return WidgetFormElement(
            getter=lambda: widget.value,
            setter=_setter,
            widgets=[ipywidgets.Box(box)],
        )

    def _construct_string(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.Text(), label=label)

    def _construct_number(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.FloatText(), label=label)

    def _construct_integer(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.IntText(), label=label)

    def _construct_boolean(self, schema, label=None, root=False):
        return self._construct_simple(schema, ipywidgets.Checkbox(), label=label)

    def _construct_null(self, schema, label=None, root=False):
        return WidgetFormElement(getter=lambda: None, setter=lambda _: None, widgets=[])

    def _construct_array(self, schema, label=None, root=False):
        if "items" not in schema:
            raise WidgetFormError("Expecting 'items' key for 'array' type")

        # Construct a widget that allows to add an array entry
        button = ipywidgets.Button(description="Add entry", icon="plus")
        vbox = ipywidgets.VBox([button])
        elements = []

        def add_entry(_):
            # if we are at the specified maximum, add should be ignored
            if "maxItems" in schema:
                if len(vbox.children) == schema["maxItems"] + 1:
                    return

            elements.insert(0, self._construct(schema["items"], label=None))
            item = elements[0].widgets[0]
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
                elements.pop(index)

            trash.on_click(remove_entry)

            def move(dir):
                def _move(b):
                    items = list(vbox.children[:-1])
                    for i, it in enumerate(items):
                        if b in it.children:
                            newi = min(max(i + dir, 0), len(items) - 1)
                            items[i], items[newi] = items[newi], items[i]
                            elements[i], elements[newi] = (
                                elements[newi],
                                elements[i],
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

        def _setter(_d):
            elements.clear()
            vbox.children = (vbox.children[-1],)
            for item in reversed(_d):
                add_entry(None)
                elements[0].setter(item)

        # If a default was specified, we now set it
        if "default" in schema:
            _setter(schema["default"])

        return WidgetFormElement(
            getter=lambda: pyrsistent.pvector(h.getter() for h in elements),
            setter=_setter,
            widgets=wrapped_vbox,
        )

    def _construct_enum(self, schema, label=None, root=False):
        # We omit trivial enums, but make sure that they end up in the result
        if len(schema["enum"]) == 1:
            return WidgetFormElement(
                getter=lambda: schema["enum"][0], setter=lambda _: None, widgets=[]
            )

        # Otherwise, we use a dropdown menu
        return self._construct_simple(
            schema, ipywidgets.Dropdown(options=schema["enum"]), label=label
        )

    def _construct_anyof(self, schema, label=None, key="anyOf"):
        names = []
        elements = []

        # Iterate over the given subschema
        for s in schema[key]:
            if "title" in s:
                names.append(s["title"])
                elements.append(self._construct(s))
            else:
                raise WidgetFormError(
                    "Schemas within anyOf/oneOf/allOf need to set the title field"
                )

        # Create the selector and subschema widget
        selector = ipywidgets.Dropdown(options=names, value=names[0])
        widget = ipywidgets.VBox([selector] + elements[0].widgets)

        # Whenever there is a change, we switch the subschema widget
        def _select(change):
            widget.children = [selector] + elements[names.index(selector.value)].widgets

        selector.observe(_select)

        def _setter(_d):
            for i, s in enumerate(schema[key]):
                try:
                    jsonschema.validate(
                        instance=pyrsistent.thaw(_d), schema=pyrsistent.thaw(s)
                    )
                    selector.value = names[i]
                    _select(None)
                except ValidationError:
                    pass

        return WidgetFormElement(
            getter=lambda: elements[names.index(selector.value)].getter(),
            setter=_setter,
            widgets=[widget],
        )


def upload_files(directory=None, filetype=""):
    """
    Create a widget to upload and store files over the jupyter interface.
    This function will be called by the different load functions.

    :param directory:
        The directory on the server where the files will be saved.
        This will be set by the function calling upload_files and be representive of the different upload types.
        eg. Pipelines will be saved in a differend directory than datasets or segmentations.
    :type directory: string
    :param filetype:
        Set the filetype filter for the upload widget
    :type filetype: string

    :return: The name(s) of the uploaded file(s)

    """
    # this needs to be loaded here to avoid circular imports
    from adaptivefiltering.apps import block_until_button_click

    if directory == None:
        print("Uploaded files will be saved in the current working directory.")
    if not os.path.isdir(directory):
        print("The directory: " + directory + "does not exist and will be created.")
        os.mkdir(directory)

    confirm_button = ipywidgets.Button(
        description="Confirm upload",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Confirm upload",
        icon="check",  # (FontAwesome names without the `fa-` prefix)
    )
    upload = ipywidgets.FileUpload(
        accept=filetype,  # Accepted file extension e.g. '.txt', '.pdf', 'image/*', 'image/*,.pdf'
        multiple=True,  # True to accept multiple files upload else False
    )

    app = ipywidgets.AppLayout(
        header=None,
        footer=ipywidgets.Box([upload, confirm_button]),
        pane_widths=[1, 0, 2],
    )
    display(app)
    block_until_button_click(confirm_button)
    app.layout.display = "none"
    uploaded_data = upload.value
    filenames = []
    for filename, uploaded_file in zip(uploaded_data.keys(), uploaded_data.values()):
        filenames.append(filename)
        with open(directory + "/" + filename, "wb") as fp:
            fp.write(uploaded_file["content"])
    return ["./" + directory + "/" + name for name in filenames]
