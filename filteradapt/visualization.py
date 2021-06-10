import ipyvolume.pylab as vis


def vis_pointcloud(x, y, z):
    fig = vis.figure(width=1000)
    vis.scatter(x, y, z, color="red", size=0.05)
    fig.xlim = (min(x), max(x))
    fig.ylim = (min(y), max(y))
    fig.zlim = (min(z), max(z))
    vis.show()
