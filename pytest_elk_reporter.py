# -*- coding: utf-8 -*-
from __future__ import print_function

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


class ElkReporter(object):
    def __init__(self, es_address, es_username, es_password):
        self.es_address = es_address
        self.es_username = es_username
        self.es_password = es_password
        if es_username and es_password:
            self.es_url = "http://{0.es_username}:{0.es_password}@{0.es_address}".format(
                self
            )
        else:
            self.es_url = "http://{0.es_address}".format(self)
        self.stats = {"passed": 0, "failed": 0, "error": 0}
        # self.git_data = dict()  # TODO: add pluging for all types of user data
        # self.jenkins_data = dict()
        self.session_data = dict(
            username=getpass.getuser(), hostname=socket.gethostname()
        )
        # self.local_test_data = dict()
        self.suite_start_time = ""

    def pytest_runtest_logreport(self, report):
        if report.passed:
            if report.when == "call":
                self.stats["passed"] += 1
                test_data = dict(
                    timestamp=datetime.datetime.utcnow().isoformat(),
                    name=report.nodeid,
                    outcome="passed",
                    duration=report.duration,
                    **self.session_data
                )
                self.post_test_results(test_data)
        elif report.failed:
            if report.when == "teardown":
                pass
            if report.when == "call":
                self.stats["failed"] += 1
                test_data = dict(
                    timestamp=datetime.datetime.utcnow().isoformat(),
                    name=report.nodeid,
                    outcome="failed",
                    duration=report.duration,
                    **self.session_data
                )
                self.post_test_results(test_data)
            else:
                self.stats["error"] += 1
                test_data = dict(
                    timestamp=datetime.datetime.utcnow().isoformat(),
                    name=report.nodeid,
                    outcome="error",
                    duration=report.duration,
                    **self.session_data
                )
                self.post_test_results(test_data)

    def pytest_sessionstart(self):
        self.suite_start_time = datetime.datetime.utcnow().isoformat()

    def pytest_sessionfinish(self):
        print(self.stats)

    def post_test_results(self, test_data):
        res = requests.post(self.es_url + "/test_stats/_doc", json=test_data)
        res.raise_for_status()


@pytest.fixture
def elk_reporter(request):
    return request.config.pluginmanager.get_plugin("elk-reporter-runtime")
