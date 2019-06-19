# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import getpass
import socket
import datetime

import pytest
import requests


def pytest_addoption(parser):
    group = parser.getgroup("elk-reporter")
    group.addoption(
        "--es-address",
        action="store",
        dest="es_address",
        default="127.0.0.1:9200",
        help="Elasticsearch addresss",
    )

    group.addoption(
        "--es-username",
        action="store",
        dest="es_username",
        default=None,
        help="Elasticsearch username",
    )

    group.addoption(
        "--es-password",
        action="store",
        dest="es_password",
        default=None,
        help="Elasticsearch password",
    )


def pytest_configure(config):
    # prevent opening elk-reporter on slave nodes (xdist)
    if not hasattr(config, "slaveinput"):
        config.elk = ElkReporter(
            es_address=config.option.es_address,
            es_username=config.option.es_username,
            es_password=config.option.es_password,
        )
        config.pluginmanager.register(config.elk, "elk-reporter-runtime")


def pytest_unconfigure(config):
    elk = getattr(config, "elk", None)
    if elk:
        del config.elk
        config.pluginmanager.unregister(elk)


def get_username():
    try:
        return getpass.getuser()
    except ImportError:
        # seem like our friends in AppVeyor took security into a new level,
        # and no username env vars casues getpass to go crazy
        # https://github.com/python-cmd2/cmd2/pull/372/files#diff-ed451f9960c50a6a096b11155fdbfc1dR325
        return "AppVeyorIt'sWeirdNotToHaveUserName"


class ElkReporter(object):
    def __init__(self, es_address, es_username, es_password):
        self.es_address = es_address
        self.es_username = es_username
        self.es_password = es_password
        self.stats = dict.fromkeys(
            ["error", "passed", "failure", "skipped", "xfailed"], 0
        )
        self.session_data = dict(username=get_username(), hostname=socket.gethostname())
        self.suite_start_time = ""

    @property
    def es_url(self):
        if self.es_username and self.es_password:
            return "http://{0.es_username}:{0.es_password}@{0.es_address}".format(self)
        return "http://{0.es_address}".format(self)

    def pytest_runtest_logreport(self, report):
        if report.passed:
            if report.when == "call":
                self.report_test(report, "passed")
        elif report.failed:
            if report.when == "teardown":
                pass
            if report.when == "call":
                self.report_test(report, "failure")
            else:
                self.report_test(report, "error")
        elif report.skipped:
            if getattr(report, "wasxfail", None) is not None:
                self.report_test(report, "xfailed")
            else:
                self.report_test(report, "skipped")

    def report_test(self, item_report, outcome):
        self.stats[outcome] += 1
        test_data = dict(
            timestamp=datetime.datetime.utcnow().isoformat(),
            name=item_report.nodeid,
            outcome=outcome,
            duration=item_report.duration,
            **self.session_data
        )
        longreprtext = getattr(item_report, "longreprtext", None)
        if longreprtext:
            test_data.update(failure_message=longreprtext)

        self.post_to_elasticsearch(test_data)

    def pytest_sessionstart(self):
        self.suite_start_time = datetime.datetime.utcnow().isoformat()

    def pytest_sessionfinish(self):
        print(self.stats)

    def post_to_elasticsearch(self, test_data):
        if self.es_address:
            res = requests.post(
                self.es_url + "/test_stats/_doc", json=test_data
            )  # TODO: have test_stats as configuration
            res.raise_for_status()


@pytest.fixture(scope="session")
def elk_reporter(request):
    return request.config.pluginmanager.get_plugin("elk-reporter-runtime")


@pytest.fixture(scope="session", autouse=True)
def jenkins_data(request):
    """
    Append jenkins job and user data into results session
    """
    # TODO: maybe filter some, like password and such ?
    jenkins_env = {
        k.lower(): v for k, v in os.environ.items() if k.startswith("JENKINS_")
    }

    elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
    elk.session_data.update(**jenkins_env)
