#!/usr/bin/env python

import os

with open(os.path.join(os.path.expanduser("~"), ".ssh/id_ed25519"), "w") as f:
    # We are running into https://github.com/readthedocs/readthedocs.org/issues/8636. Therefore,
    # we absolutely need to elimiate the single quotes.  
    f.write(os.environ["SSH_KEY"].strip("'"))
