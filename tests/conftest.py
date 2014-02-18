import pytest

from pydap.responses.aaigrid import AAIGridResponse

@pytest.fixture
def app():
    return AAIGridResponse(None)
