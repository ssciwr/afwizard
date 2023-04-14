#!/usr/bin/env python

from afwizard.paths import download_test_file, nakadake_data

# Pre-fetch all the Nakadake data
for filename in nakadake_data.registry:
    nakadake_data.fetch(filename)

# Also pre-fetch testing data
download_test_file("blubb")
