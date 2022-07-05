Extending AFwizard with custom backends
=======================================

In this section, we will describe how the :code:`afwizard` data model
can be extended with custom backends. Such extensions can be done from your project
that depends on :code:`afwizard` - you do not necessarily need to contribute
your custom backend to :code:`afwizard` for it to integrate with the rest of
:code:`afwizard`.

In this documentation we will treat the following use case: You do have an
executable :code:`myfilter` that performs ground point filtering. It accepts
an LAS input filename, an output filename and floating point finetuning value
as command line arguments. You want to expose this filtering backend in
:code:`afwizard`.

.. note::

   This is an advanced topic. A certain familiarity with object-oriented
   Python programming is required to understand and productively use this
   feature.

The filter backend class
------------------------

Custom backends are created by inheriting from the :class:`afwizard.filter.Filter`
class. When inheriting, your derived class needs to specify an :code:`identifier` that
will be used to register your derived class with the base class. Having done that you only
need to implement two methods on the derived class: :code:`schema` describes the
configuration space of your custom backend and :code:`execute` contains the execution
logic of your backend:

.. code:: python

    import afwizard
    import shutil
    import subprocess

    class MyBackend(afwizard.filter.Filter, identifier="mybackend"):
        @classmethod
        def schema(cls):
            # The configuration schema here follows the JSONSchema standard.
            return {
                "anyOf": [
                    {
                        "type": "object",
                        "title": "My Filtering Backend",
                        "properties": {
                            "_backend": {
                                "type": "string",
                                "const": "mybackend",
                            },
                            "myparameter": {
                                "type": "number",
                                "default": 0.5,
                                "title": "My tuning parameter",
                            }
                        },
                    }
                ]
            }

        def execute(self, dataset):
            # Ensure that the dataset is of type DataSet (maybe applying conversion)
            dataset = afwizard.DataSet.convert(dataset)

            # Create a temporary filename for the output
            filename = afwizard.paths.get_temporary_filename("las")

            # Run the filter program as a subprocess
            subprocess.run(
                ["myfilter", dataset.filename, filename, self.config["myparameter"]],
                check=True,
            )

            # Construct a new DataSet object with the result
            return afwizard.DataSet(filename, spatial_reference=dataset.spatial_reference)

        @classmethod
        def enabled(cls):
            # We only enable this backend if the executable 'myfilter' is in our path
            return shutil.which("myfilter") is not None

The implementation of :code:`schema` needs to return a dictionary that follows the
JSONSchema specification. If you do not know JSONSchema, you might want to read this
introduction guide: `Understanding JSONSchema`_. We require the schema for your filter
to be wrapped into an :code:`anyOf` rule that allows schema composition between backends.
This :code:`anyOf` rule does also allow you to expose multiple filters per backend class
(e.g. because they share the same execution logic). Each of the schemas contained in
the :code:`anyOf` rule must be of type :code:`object` and define at least the :code:`_backend`
property as shown in the code example.

The :code:`execute` method implements the core functionality of your filter. It is passed
a dataset and returns a filtered dataset. We first assert that we are dealing with a dataset
that is represented by a LAS file by converting it to :class:`afwizard.DataSet`.
The actual execution is done using :code:`subprocess.run`.

The :code:`enabled` method in the above can be used to exclude the custom backend if
some condition is not met e.g. the necessary executable was not found. This methods defaults
to :code:`True`.

.. _Understanding JSONSchema: https://json-schema.org/understanding-json-schema

Using a custom backend class
----------------------------

As backend classes register themselves with the base class, it is only necessary to ensure
that the module that contains the class has been imported before other functionality of
:code:`afwizard` is used. This can e.g. be done from :code:`__init__.py`.

Backends that operate on custom data representations
----------------------------------------------------

In above example, the ground point filtering algorithm operated directly on LAS files
from the file system. Other backends might operate on other data representations, e.g.
OPALS is working with its own *OPALS Data Manager* object. If your backend should work
on a different representation, you can inherit from :class:`afwizard.DataSet` and implement the following
methods which are shown as no-op here:

.. code:: python

    class CustomDataSet(afwizard.DataSet):
        @classmethod
        def convert(cls, dataset):
            # Make sure that conversion is idempotent
            if isinstance(dataset, CustomDataSet):
                return dataset

            # Here, you can do custom things

            return CustomDataSet(dataset.filename, dataset.spatial_reference)

        def save(self, filename, overwrite=False):
            # Save the dataset as LAS - using DataSet here
            return DataSet.convert(self).save(filename, overwrite=overwrite)

The :code:`convert` method will be used by filters to ensure the correct
dataset representation as shown in above example.
