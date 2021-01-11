import re

import pytest
import requests_mock as rm_module


pytest_plugins = "pytester"  # pylint: disable=invalid-name


@pytest.fixture(scope="function")  # executed on every test
def requests_mock():
    """Mock out the requests component of your code with defined responses.
    Mocks out any requests made through the python requests library with useful
    responses for unit testing. See:
    https://requests-mock.readthedocs.io/en/latest/
    """
    kwargs = {"real_http": False}

    with rm_module.Mocker(**kwargs) as mock:
        yield mock


@pytest.fixture(scope="function", autouse=True)
def configure_es_mock(requests_mock):  # pylint: disable=redefined-outer-name
    matcher = re.compile(r"http://127.0.0.1:9200/test_data/.*")
    requests_mock.post(
        matcher,
        response_list=[
            dict(
                text='{"aggregations": {"percentiles_duration": {"values": {"95.0": 60.0}}}}',
                status_code=201,
            ),
            dict(
                text='{"aggregations": {"percentiles_duration": {"values": {"95.0": 60.0}}}}',
                status_code=201,
            ),
            dict(
                text='{"aggregations": {"percentiles_duration": {"values": {"95.0": 120.0}}}}',
                status_code=201,
            ),
            dict(
                text='{"aggregations": {"percentiles_duration": {"values": {"95.0": null}}}}',
                status_code=201,
            ),
            dict(text="should error !!!", status_code=500),
        ],
    )
