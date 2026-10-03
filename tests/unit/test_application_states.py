import pytest
from jobhunt_domain.application_states import (
    APPLICATION_STATES,
    assert_transition,
    can_transition,
)


def test_application_happy_path():
    assert "started" in APPLICATION_STATES
    assert can_transition("started", "applied")
    assert can_transition("applied", "interview")
    assert can_transition("interview", "offer")


def test_application_illegal():
    assert not can_transition("rejected", "applied")
    with pytest.raises(ValueError):
        assert_transition("offer", "started")


def test_idempotent_same_state():
    assert can_transition("applied", "applied")
