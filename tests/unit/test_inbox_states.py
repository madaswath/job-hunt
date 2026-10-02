import pytest
from jobhunt_domain.inbox_states import assert_transition, can_transition


def test_happy_path():
    assert can_transition("captured", "normalized")
    assert can_transition("normalized", "matched")
    assert can_transition("matched", "review_required")


def test_illegal_skip():
    assert not can_transition("captured", "applied")
    with pytest.raises(ValueError):
        assert_transition("captured", "applied")
