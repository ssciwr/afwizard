#!/usr/bin/env python

from afwizard.paths import nakadake_data

# Pre-fetch all the Nakadake data
for filename in nakadake_data.registry:
    nakadake_data.fetch(filename)
