import adaptivefiltering


def test_version():
    vers = adaptivefiltering.__version__
    assert len(vers.split(".")) == 3


def test_print_version(capsys):
    adaptivefiltering.print_version()
    read = capsys.readouterr().out
    assert len(read.split(".")) == 3
