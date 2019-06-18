# -*- coding: utf-8 -*-

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("elk-reporter")
    group.addoption(
        "--foo",
        action="store",
        dest="dest_foo",
        default="2019",
        help='Set the value for the fixture "bar".',
    )

    parser.addini("HELLO", "Dummy pytest.ini setting")


@pytest.fixture
def bar(request):  # pylint: disable=blacklisted-name
    return request.config.option.dest_foo
