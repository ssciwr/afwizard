from adaptivefiltering.paths import locate_file, get_temporary_filename
from adaptivefiltering.utils import AdaptiveFilteringError

import functools
import os
import shutil
import sys


class DataSet:
    def __init__(self, filename=None, provenance=[]):
        """The main class that represents a Lidar data set.

        :param filename:
            Filename to load the dataset from. The dataset is expected to be in LAS/LAZ 1.2-1.4 format.
            If an absolute filename is given, the dataset is loaded from that location. Relative paths
            are interpreted (in this order) with respect to the directory set with :func:`~adaptivefiltering.set_data_directory`,
            the current working directory, XDG data directories (Unix only) and the Python package
            installation directory.
            Will give a warning if too many data points are present.
        :type filename: str
        """
        # initilizise self._geo_tif_data_resolution as 0
        self._geo_tif_data_resolution = 0

        # Store the given parameters
        self._provenance = provenance
        self.filename = filename

        # Make the path absolute
        if self.filename is not None:
            self.filename = locate_file(self.filename)

    def save_mesh(
        self,
        filename,
        resolution=2.0,
    ):
        """Store the point cloud as a digital terrain model to a GeoTIFF file

        It is important to note that for archaelogic applications, the mesh is not
        a traditional DEM/DTM (Digitial Elevation/Terrain Model), but rather a DFM
        (Digital Feature Model) which consists of ground and all potentially relevant
        structures like buildings etc. but always excludes vegetation.

        :param filename:
            The filename to store the mesh. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str
        :param resolution:
            The mesh resolution in meters. Adapt this depending on the scale
            of the features you are looking for and the point density of your
            Lidar data.
        :type resolution: float
        """
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        dataset = PDALInMemoryDataSet.convert(self)
        return dataset.save_mesh(filename, resolution=resolution)

    def show_mesh(self, resolution=2.0):
        """Visualize the point cloud as a digital terrain model in JupyterLab

        It is important to note that for archaelogic applications, the mesh is not
        a traditional DEM/DTM (Digitial Elevation/Terrain Model), but rather a DFM
        (Digital Feature Model) which consists of ground and all potentially relevant
        structures like buildings etc. but always excludes vegetation.

        :param resolution:
            The mesh resolution in meters. Adapt this depending on the scale
            of the features you are looking for and the point density of your
            Lidar data.
        :type resolution: float
        """
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        dataset = PDALInMemoryDataSet.convert(self)
        return dataset.show_mesh(resolution=resolution)

    def show_points(self, threshold=750000):
        """Visualize the point cloud in Jupyter notebook
        Will give a warning if too many data points are present.
        Non-operational if called outside of Jupyter Notebook.
        """
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        dataset = PDALInMemoryDataSet.convert(self)
        return dataset.show_points(threshold=threshold)

    def show_hillshade(self, resolution=2.0):
        """Visualize the point cloud as hillshade model in Jupyter notebook"""
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        dataset = PDALInMemoryDataSet.convert(self)
        return dataset.show_hillshade(resolution=resolution)

    def save(self, filename, compress=False, overwrite=False):
        """Store the dataset as a new LAS/LAZ file

        This writes this instance of the data set to an LAS/LAZ file which will
        permanently store the ground point classification. The resulting file will
        also contain the point data from the original data set.

        :param filename:
            Where to store the new LAS/LAZ file. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str
        :param compress:
            If true, an LAZ file will be written instead of an LAS file.
        :type compress: bool
        :param overwrite:
            If this parameter is false and the specified filename does already exist,
            an error is thrown. This is done in order to prevent accidental corruption
            of valueable data files.
        :type overwrite: bool
        :return:
            A dataset object wrapping the written file
        :rtype: adaptivefiltering.DataSet
        """
        # If the filenames match, this is a no-op operation
        if filename == self.filename:
            return

        # Otherwise, we can simply copy the file to the new location
        # after checking that we are not accidentally overriding something
        if not overwrite and os.path.exists(filename):
            raise AdaptiveFilteringError(
                f"Would overwrite file '{filename}'. Set overwrite=True to proceed"
            )

        # Do the copy operation
        shutil.copy(self.filename, filename)

        # And return a DataSet instance
        return DataSet(filename=filename)

    def restrict(self, segmentation):
        """Restrict the data set to a spatial subset

        :param segmentation:
        :type: adaptivefiltering.segmentation.Segmentation
        """
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        dataset = PDALInMemoryDataSet.convert(self)
        return dataset.restrict(segmentation)

    def provenance(self, stream=sys.stdout):
        """Report the provence of this data set

        For the given data set instance, report the input data and filter
        sequence (incl. filter settings) that procuced this data set. This
        can be used to make good filtering results achieved while using the
        package reproducible.

        :param stream:
            The stream to write the results to. Defaults to stdout, but
            could also e.g. be a file stream.
        """

        stream.write("Provenance report generated by adaptivefiltering:\n\n")
        for i, entry in self._provenance:
            stream.write(f"Item #{i}:\n")
            stream.write(f"{entry}\n\n")

    @classmethod
    def convert(cls, dataset):
        """Convert this dataset to an instance of DataSet"""
        return dataset.save(get_temporary_filename(extension="las"))


class ASPRSClassification:
    """A data structure that describes the ASPRS Standard Lidar Point Classes"""

    @functools.lru_cache
    def _mapping(cls):
        """Mapping of string names to classification values.

        This only exposes the subset relevant to our use cases
        """
        return {
            "unclassified": 1,
            "ground": 2,
            "low_vegetation": 3,
            "medium_vegetation": 4,
            "high_vegetation": 5,
            "building": 6,
            "low_point": 7,
            "water": 9,
            "road_surface": 11,
        }

    def __getitem__(self, class_):
        """Create a classification value sequence from input"""

        # This might be a slice, which we will resolve to an integer sequence
        if isinstance(class_, slice):
            # If start is not given, it is zero
            start = class_.start
            if start is None:
                start = 0

            # If stop is not given, it is the maximum possible classification value: 255
            stop = class_.stop
            if stop is None:
                stop = 255
            # This adaptation is necessary to be able to use the range generator below
            stop = stop + 1

            # Collect the list of arguments to the range generator
            args = [start, stop]

            # Add a third parameter iff the slice step parameter was given
            if class_.step is not None:
                args.append(class_.step)

            # Return the tuple of classification values
            return tuple(range(*args))

        def _process_list_item(item):
            """Process a single given classification value"""
            if isinstance(item, str):
                # If this is a string we try to split it at commas
                subitems = item.split(",")
                if len(subitems) > 1:
                    # If a comma-separated list was given, we return the union of classification
                    # values for each of the entries of that list
                    return sum((_process_list_item(i.strip()) for i in subitems), ())
                else:
                    try:
                        # For strings, we do a lookup in our internal name mapping
                        return (self._mapping()[item.strip()],)
                    except KeyError:
                        raise AdaptiveFilteringError("Classifier not known")

            # If no string was given, we assume that a plain integer was given
            assert isinstance(item, int)
            return (item,)

        def _sort_uniq(items):
            return tuple(sorted(set(items)))

        # If a tuple of items was given, we return the union of classification values
        if isinstance(class_, tuple):
            return _sort_uniq(sum((_process_list_item(i) for i in class_), ()))
        else:
            return _sort_uniq(_process_list_item(class_))


# A global object of type ASPRSClassification is available for simple use
asprs = ASPRSClassification()
