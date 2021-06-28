import ipyvolume.pylab as vis


def vis_pointcloud(x, y, z):
    """Visualization of a point cloud in Jupyter notebooks

    :param x: The array x-coordinates of the point cloud
    :param y: The array y-coordinates of the point cloud
    :param z: The array z-coordinates of the point cloud
    :type x: numpy.array
    :type y: numpy.array
    :type z: numpy.array
    """
    fig = vis.figure(width=1000)
    vis.scatter(
        x,
        y,
        z,
        color="red",
        size=0.05,
    )
    vis.style.box_off()
    vis.view(azimuth=180, elevation=90)
    fig.xlim = (min(x), max(x))
    fig.ylim = (min(y), max(y))
    fig.zlim = (min(z), max(z))
    vis.show()
