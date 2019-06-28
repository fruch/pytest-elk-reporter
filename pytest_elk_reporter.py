# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import getpass
import socket
import datetime
import logging
import subprocess
from collections import defaultdict

import six
import pytest
import requests

LOGGER = logging.getLogger("elk-reporter")


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
        default="",
        help="Elasticsearch username",
    )

    group.addoption(
        "--es-password",
        action="store",
        dest="es_password",
        default="",
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


class ElkReporter(object):  # pylint: disable=too-many-instance-attributes
    def __init__(self, es_address, es_username, es_password):
        self.es_address = es_address
        self.es_username = es_username
        self.es_password = es_password
        self.stats = dict.fromkeys(
            [
                "error",
                "passed",
                "failure",
                "skipped",
                "xfailed",
                "xpass",
                "passed & error",
                "failure & error",
                "skipped & error",
            ],
            0,
        )
        self.session_data = dict(username=get_username(), hostname=socket.gethostname())
        self.test_data = defaultdict(dict)
        self.suite_start_time = ""
        self.reports = {}

    @property
    def es_auth(self):
        return (self.es_username, self.es_password)

    @property
    def es_url(self):
        return "http://{0.es_address}".format(self)

    def append_test_data(self, request, test_data):
        self.test_data[request.node.nodeid].update(**test_data)

    def cache_report(self, report_item, outcome):
        nodeid = getattr(report_item, "nodeid", report_item)
        # local hack to handle xdist report order
        slavenode = getattr(report_item, "node", None)
        self.reports[nodeid, slavenode] = (report_item, outcome)

    def get_report(self, report_item):
        nodeid = getattr(report_item, "nodeid", report_item)
        # local hack to handle xdist report order
        slavenode = getattr(report_item, "node", None)
        return self.reports.get((nodeid, slavenode), None)

    @staticmethod
    def get_failure_messge(item_report):
        if hasattr(item_report, "longreprtext"):
            message = item_report.longreprtext
        elif hasattr(item_report.longrepr, "reprcrash"):
            message = item_report.longrepr.reprcrash.message
        elif isinstance(item_report.longrepr, six.string_types):
            message = item_report.longrepr
        else:
            message = str(item_report.longrepr)
        return message

    def pytest_runtest_logreport(self, report):
        # pylint: disable=too-many-branches

        if report.passed:
            if report.when == "call":
                if hasattr(report, "wasxfail"):
                    self.cache_report(report, "xpass")
                else:
                    self.cache_report(report, "passed")
        elif report.failed:
            if report.when == "call":
                self.cache_report(report, "failure")
            elif report.when == "setup":
                self.cache_report(report, "error")
        elif report.skipped:
            if hasattr(report, "wasxfail"):
                self.cache_report(report, "xfailed")
            else:
                self.cache_report(report, "skipped")

        if report.when == "teardown":
            old_report = self.get_report(report)
            if report.passed:
                self.report_test(old_report[0], old_report[1])
            if report.failed:
                self.report_test(
                    report, old_report[1] + " & error", old_report=old_report[0]
                )
            if report.skipped:
                self.report_test(report, "skipped")

    def report_test(self, item_report, outcome, old_report=None):
        self.stats[outcome] += 1
        test_data = dict(
            timestamp=datetime.datetime.utcnow().isoformat(),
            name=item_report.nodeid,
            outcome=outcome,
            duration=item_report.duration,
            **self.session_data
        )
        test_data.update(self.test_data[item_report.nodeid])
        del self.test_data[item_report.nodeid]

        message = self.get_failure_messge(item_report)
        if old_report:
            message += self.get_failure_messge(old_report)
        if message:
            test_data.update(failure_message=message)

        self.post_to_elasticsearch(test_data)

    def pytest_sessionstart(self):
        self.suite_start_time = datetime.datetime.utcnow().isoformat()

    def pytest_sessionfinish(self):
        test_data = dict(summery=True, stats=self.stats, **self.session_data)
        self.post_to_elasticsearch(test_data)

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep(
            "-", "stats posted to elasticsearch: %s" % (self.stats)
        )

    def pytest_internalerror(self, excrepr):
        test_data = dict(
            timestamp=datetime.datetime.utcnow().isoformat(),
            outcome="internal-error",
            faiure_message=excrepr,
            **self.session_data
        )
        self.post_to_elasticsearch(test_data)

    def post_to_elasticsearch(self, test_data):
        if self.es_address:
            try:
                res = requests.post(
                    self.es_url + "/test_stats/_doc", json=test_data, auth=self.es_auth
                )  # TODO: have test_stats as configuration
                res.raise_for_status()
            except Exception as ex:  # pylint: disable=broad-except
                LOGGER.warning("Failed to POST to elasticsearch: [%s]", str(ex))


@pytest.fixture(scope="session")
def elk_reporter(request):
    return request.config.pluginmanager.get_plugin("elk-reporter-runtime")


@pytest.fixture(scope="session", autouse=True)
def jenkins_data(request):
    """
    Append jenkins job and user data into results session
    """
    # TODO: maybe filter some, like password/token and such ?
    jenkins_env = {
        k.lower(): v for k, v in os.environ.items() if k.startswith("JENKINS_")
    }

    elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
    elk.session_data.update(**jenkins_env)


@pytest.fixture(scope="session", autouse=True)
def circle_data(request):
    """
    Append circle ci job and user data into results session
    """
    if os.environ.get("CIRCLECI", False) == "true":
        # TODO: maybe filter some, like password/token and such ?
        circle_env = {
            k.lower(): v for k, v in os.environ.items() if k.startswith("CIRCLE_")
        }

        elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
        elk.session_data.update(**circle_env)


@pytest.fixture(scope="session", autouse=True)
def travis_data(request):
    """
    Append travis ci job and user data into results session
    """
    if os.environ.get("TRAVIS", False) == "true":
        travis_env = {
            k.lower(): v for k, v in os.environ.items() if k.startswith("TRAVIS_")
        }

        elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
        elk.session_data.update(**travis_env)


@pytest.fixture(scope="session", autouse=True)
def git_data(request):
    """
    Append git information into results session
    """
    git_info = dict()
    cmds = (
        ("git_commit_oneline", "git log --oneline  -1 --no-decorate"),
        ("git_commit_full", "git log -1 --no-decorate"),
        ("git_commit_sha", "git rev-parse HEAD"),
        ("git_commit_sha_short", "git rev-parse --short HEAD"),
        ("git_branch", "git rev-parse --abbrev-ref HEAD"),
        ("git_repo", "git config --get remote.origin.url"),
    )
    for key, command in cmds:
        try:
            git_info[key] = (
                subprocess.check_output(command, shell=True).decode("utf-8").strip()
            )
        except subprocess.CalledProcessError:
            pass
    elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
    elk.session_data.update(**git_info)
