from adaptivefiltering.paths import load_schema

import collections
import ipywidgets
import ipywidgets_jsonschema
import jsonschema
import os
import pyrsistent
import re


class WidgetFormWithLabels(ipywidgets_jsonschema.Form):
    """A subclass of WidgetForm that creates a label selection widget for arrays of strings"""

    def _construct_array(self, schema, label=None, root=False):
        if "items" not in schema:
            raise ipywidgets_jsonschema.form.FormError(
                "Expecting 'items' key for 'array' type"
            )

        # Assert a number of conditions that must be true for us
        # to create a label widget instead of the regular array
        if (
            "type" not in schema["items"]
            or schema["items"]["type"] != "string"
            or "maxItems" in schema["items"]
            or "minItems" in schema["items"]
        ):
            return super()._construct_array(schema, label=label, root=root)

        # List of widgets for later use in VBox
        widgets = []
        if "title" in schema:
            widgets.append(ipywidgets.Label(schema["title"]))

        # Create the relevant widget
        widget = ipywidgets.TagsInput(
            value=[], allow_duplicates=False, tooltip=schema.get("description", None)
        )
        widgets.append(widget)

        # Function to check a potential given pattern
        def _change_checker(change):
            if "pattern" in schema["items"]:
                for val in change["new"]:
                    if not re.fullmatch(schema["items"]["pattern"], val):
                        widget.value = [i for i in widget.value if i != val]

        widget.observe(_change_checker, names="value")

        def _register_observer(h, n, t):
            widget.observe(h, names=n, type=t)

        def _setter(_d):
            widget.value = pyrsistent.thaw(_d)

        return self.construct_element(
            getter=lambda: pyrsistent.pvector(widget.value),
            setter=_setter,
            widgets=[ipywidgets.VBox(widgets)],
            register_observer=_register_observer,
        )


BatchDataWidgetFormElement = collections.namedtuple(
    "BatchDataWidgetFormElement",
    [
        "getter",
        "setter",
        "widgets",
        "subelements",
        "batchdata_getter",
        "batchdata_setter",
        "register_observer",
    ],
)


class BatchDataWidgetForm(WidgetFormWithLabels):
    def construct_element(
        self,
        getter=lambda: None,
        setter=lambda _: None,
        widgets=[],
        subelements=[],
        batchdata_getter=lambda: [],
        batchdata_setter=lambda _: None,
        register_observer=lambda h, n, t: None,
    ):
        return BatchDataWidgetFormElement(
            getter=getter,
            setter=setter,
            widgets=widgets,
            subelements=subelements,
            batchdata_getter=batchdata_getter,
            batchdata_setter=batchdata_setter,
            register_observer=register_observer,
        )

    @property
    def batchdata(self):
        bdata = self._form_element.batchdata_getter()
        schema = load_schema("variability.json")
        jsonschema.validate(bdata, schema=schema)
        return bdata

    @batchdata.setter
    def batchdata(self, _data):
        self._form_element.batchdata_setter(_data)

    def _construct_simple(self, schema, widget, label=None, root=False):
        # Call the original implementation to get the basic widget
        original = super()._construct_simple(schema, widget, label=label, root=root)

        # If this is something that for some reason did not produce an input
        # widget, we skip all the variablity part.
        if len(original.widgets) == 0:
            return original

        # Create additional controls for batch processing and variability

        # Two buttons that allow to create the additional input
        b1 = ipywidgets.ToggleButton(
            icon="layer-group", tooltip="Use a parameter batch for this parameter"
        )
        b2 = ipywidgets.ToggleButton(
            icon="sitemap", tooltip="Add a variability to this parameter"
        )

        # The widget where the variablility input is specified
        var = ipywidgets.Text(
            tooltip="Use comma separation to specify a discrete set of parameters or dashes to define a parameter range"
        )

        # For persisitent variability, we also need some additional information
        name = ipywidgets.Text(
            tooltip="The parameter name to use for this variability. Will be displayed to the end user."
        )
        descr = ipywidgets.Text(
            tooltip="The description of this parameter that will be displayed to the end user when hovering over the parameter."
        )

        # A container widget that allows us to easily make the input widget vanish
        box = ipywidgets.VBox()

        # The handler that unfolds the input widget if necessary
        def handler(change):
            # Make sure that the two toggle buttons are mutually exclusive
            if b1.value and b2.value:
                for b in [b1, b2]:
                    if b is not change.owner:
                        b.value = False
                        return

            # Make sure that if either button is pressed, we display the input widget
            if b1.value:
                box.children = (ipywidgets.HBox([ipywidgets.Label("Values:"), var]),)
            elif b2.value:
                box.children = (
                    ipywidgets.HBox([ipywidgets.Label("Values:"), var]),
                    ipywidgets.HBox([ipywidgets.Label("Name:"), name]),
                    ipywidgets.HBox([ipywidgets.Label("Description:"), descr]),
                )
            else:
                box.children = ()

        b1.observe(handler, names="value")
        b2.observe(handler, names="value")

        # Modify the original widgets to also include our modifications
        original.widgets[0].children[-1].layout = ipywidgets.Layout(width="70%")
        b1.layout = ipywidgets.Layout(width="15%")
        b2.layout = ipywidgets.Layout(width="15%")
        original.widgets[0].children = original.widgets[0].children[:-1] + (
            ipywidgets.HBox([original.widgets[0].children[-1], b1, b2]),
        )
        original.widgets[0].children = original.widgets[0].children + (box,)

        # Lazy evalution of the batch data
        def _getter():
            ret = []

            # Only record a variation if one of our buttons is pressed
            if b1.value or b2.value:
                ret.append(
                    {
                        "values": var.value,
                        "persist": b2.value,
                        "path": [],
                        "name": name.value,
                        "description": descr.value,
                        "type": schema["type"],
                    }
                )

            return ret

        def _setter(_data):
            assert len(_data) == 1
            var.value = _data[0]["values"]
            name.value = _data[0]["name"]
            descr.value = _data[0]["description"]
            if _data[0].get("persist", False):
                b2.value = True
            else:
                b1.value = True

        def _register_observer(h, n, t):
            original.register_observer(h, n, t)
            b1.observe(h, names=n, type=t)
            b2.observe(h, names=n, type=t)
            var.observe(h, names=n, type=t)
            name.observe(h, names=n, type=t)
            descr.observe(h, names=n, type=t)

        # Wrap the result in our new form element
        return self.construct_element(
            getter=original.getter,
            setter=original.setter,
            widgets=original.widgets,
            batchdata_getter=_getter,
            batchdata_setter=_setter,
            register_observer=_register_observer,
        )

    def _construct_object(self, schema, label=None, root=False):
        original = super()._construct_object(schema, label=label, root=root)

        def _getter():
            ret = []

            # Iterate over the subelements and update their path
            for key, subel in original.subelements.items():
                data = subel.batchdata_getter()
                for d in data:
                    d["path"].append({"key": key})
                ret.extend(data)

            return ret

        def _setter(_data):
            for _d in _data:
                key = _d["path"][0]["key"]
                _d["path"] = _d["path"][1:]
                original.subelements[key].batchdata_setter([_d])

        return self.construct_element(
            getter=original.getter,
            setter=original.setter,
            widgets=original.widgets,
            subelements=original.subelements,
            batchdata_getter=_getter,
            batchdata_setter=_setter,
            register_observer=original.register_observer,
        )

    def _construct_array(self, schema, label=None, root=False):
        original = super()._construct_array(schema, label=label, root=root)

        def _getter():
            ret = []

            for i, subel in enumerate(original.subelements):
                data = subel.batchdata_getter()
                for d in data:
                    d["path"].append({"index": i})
                ret.extend(data)

            return ret

        def _setter(_data):
            for _d in _data:
                index = _d["path"][0]["index"]
                _d["path"] = _d["path"][1:]
                original.subelements[index].batchdata_setter([_d])

        return self.construct_element(
            getter=original.getter,
            setter=original.setter,
            widgets=original.widgets,
            subelements=original.subelements,
            batchdata_getter=_getter,
            batchdata_setter=_setter,
            register_observer=original.register_observer,
        )

    def _construct_anyof(self, schema, label=None, key="anyOf"):
        original = super()._construct_anyof(schema, label, key)
        selector = original.widgets[0].children[0]

        def _setter(_data):
            for subel in original.subelements:
                try:
                    subel.batchdata_setter(_data)
                    return
                except (KeyError, IndexError):
                    pass

            raise ipywidgets_jsonschema.form.FormError(
                "Cannot restore batchdata in anyOf schema"
            )

        return self.construct_element(
            getter=original.getter,
            setter=original.setter,
            widgets=original.widgets,
            subelements=original.subelements,
            batchdata_getter=lambda: original.subelements[
                selector.index
            ].batchdata_getter(),
            batchdata_setter=_setter,
            register_observer=original.register_observer,
        )


def upload_button(directory=None, filetype=""):
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
    from adaptivefiltering.apps import create_upload

    def _save_data(uploaded_files):
        filenames = []
        for filename, uploaded_file in uploaded_files.value.items():
            filenames.append(filename)
            print(filename)
            with open(os.path.join(directory, filename), "wb") as fp:
                fp.write(uploaded_file["content"])
        return [os.path.join(directory, filename) for name in filenames]

    if directory is None:
        print("Uploaded files will be saved in the current working directory.")
        directory = os.getcwd()
    elif not os.path.isdir(directory):
        print("The directory: " + directory + "does not exist and will be created.")
        os.mkdir(directory)

    return create_upload(filetype, finalization_hook=_save_data)
