import afwizard


def test_version():
    vers = afwizard.__version__
    assert len(vers.split(".")) == 3


def test_print_version(capsys):
    afwizard.print_version()
    read = capsys.readouterr().out
    assert len(read.split(".")) == 3
