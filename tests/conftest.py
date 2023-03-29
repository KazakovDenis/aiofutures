import pytest

from aiofutures import AsyncExecutor


@pytest.fixture(scope='session')
def executor():
    return AsyncExecutor()
