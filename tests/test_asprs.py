from adaptivefiltering.asprs import *

import pytest


def test_asprs_classification():
    assert asprs[42] == (42,)
    assert asprs["ground"] == (2,)
    assert asprs[42, 17] == (17, 42)
    assert asprs[42, "ground"] == (2, 42)
    assert asprs["low_vegetation", "ground"] == (2, 3)
    assert asprs["low_vegetation  ", " ground "] == (2, 3)
    assert asprs["low_vegetation,ground"] == (2, 3)
    assert asprs["  low_vegetation ,  ground"] == (2, 3)
    assert asprs[2:4] == (2, 3, 4)
    assert asprs[2:4:2] == (2, 4)
    assert asprs[:4] == (0, 1, 2, 3, 4)
    assert asprs[253:] == (253, 254, 255)
    assert len(asprs[:]) == 256

    with pytest.raises(AdaptiveFilteringError):
        asprs["non-existing"]

    with pytest.raises(AdaptiveFilteringError):
        asprs[-1]

    with pytest.raises(AdaptiveFilteringError):
        asprs[256]
