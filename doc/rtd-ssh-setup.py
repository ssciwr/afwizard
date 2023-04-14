#!/usr/bin/env python

import os

# Define relevant variable names
sshpath = os.path.join(os.path.expanduser("~"), ".ssh")
keyfile = os.path.join(sshpath, "id_ed25519")
knownhosts = os.path.join(sshpath, "known_hosts")

# Create SSH folder
os.makedirs(sshpath)

# Write key into correct file
with open(keyfile, "w") as f:
    # We need to reconstruct the keyfile from our env variable, because
    # https://github.com/readthedocs/readthedocs.org/issues/8636 makes our
    # input absolutely unusable.
    f.write("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    for line in os.environ["SSH_KEY"].strip("'").split(":"):
        f.write(line + "\n")
    f.write("-----END OPENSSH PRIVATE KEY-----\n")

# Manipulate file permissions
os.chmod(keyfile, 0o600)

# Add our server to known hosts
with open(knownhosts, "w") as f:
    f.write(
        "ssc-jupyter.iwr.uni-heidelberg.de ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJlEBwr7Qv0expAPxukZOmIUcVI1erVPya+GkzCd+iQK\n"
    )
