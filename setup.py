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
        "Click",
        "gdal",
        "geodaisy",
        "geojson",
        "ipympl",
        "ipython_blocking",
        "IPython==7.21.0",
        "ipyvolume",
        "ipywidgets<8",
        "jsonschema",
        "matplotlib",
        "numpy",
        "pyrsistent",
        "xdg",
        "xmltodict",
    ],
    entry_points="""
        [console_scripts]
        extract_opals_schema=adaptivefiltering.opals:_automated_opals_schema
    """,
    include_package_data=True,
    package_data={"": ["data/*", "schema/*", "schema/*/*"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
)
