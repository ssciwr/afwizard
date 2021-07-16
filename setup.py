from setuptools import find_packages, setup

setup(
    name="adaptivefiltering",
    version="0.0.1",
    author="Dominic Kempf",
    author_email="ssc@iwr.uni-heidelberg.de",
    description="Adaptive Ground Point Filtering Library",
    long_description="*This library is currently under development.*",
    packages=find_packages(),
    install_requires=[
        "gdal",
        "geodaisy",
        "geojson",
        "ipyvolume",
        "ipywidgets<8",
        "jsonschema",
        "matplotlib",
        "numpy",
        "pyrsistent",
        "xdg",
        "xmltodict",
    ],
    include_package_data=True,
    package_data={"": ["data/*", "schema/*", "schema/*/*"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
)
