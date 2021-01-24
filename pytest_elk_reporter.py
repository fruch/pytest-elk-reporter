# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import getpass
import socket
import datetime
import logging
import subprocess
from collections import defaultdict
import pprint
import fnmatch
import concurrent.futures

import six
import pytest
import requests
from _pytest.runner import pytest_runtest_makereport as _makereport


LOGGER = logging.getLogger("elk-reporter")


def pytest_runtest_makereport(item, call):
    report = _makereport(item, call)
    report.keywords = list([m.name for m in item.iter_markers()])
    return report


def pytest_addoption(parser):
    group = parser.getgroup("elk-reporter")
    group.addoption(
        "--es-address",
        action="store",
        dest="es_address",
        default=None,
        help="Elasticsearch address",
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

    group.addoption(
        "--es-timeout",
        action="store",
        dest="es_timeout",
        default=10,
        help="Elasticsearch connection timeout",
    )

    group.addoption(
        "--es-slices",
        action="store_true",
        dest="es_slices",
        default=False,
        help="Splice collected tests base on history data",
    )

    group.addoption(
        "--es-max-splice-time",
        action="store",
        type=float,
        dest="es_max_splice_time",
        default=60,
        help="Max duration of each splice, in minutes",
    )
    group.addoption(
        "--es-default-test-time",
        action="store",
        type=float,
        dest="es_default_test_time",
        default=120,
        help="Default time for a test, if history isn't found for it, in seconds",
    )

    parser.addini("es_address", help="Elasticsearch address", default=None)
    parser.addini("es_username", help="Elasticsearch username", default=None)
    parser.addini("es_password", help="Elasticsearch password", default=None)
    parser.addini(
        "es_index_name",
        help="name of the elasticsearch index to save results to",
        default="test_data",
    )


def pytest_configure(config):
    # prevent opening elk-reporter on slave nodes (xdist)
    if not hasattr(config, "slaveinput"):

        config.elk = ElkReporter(config)
        config.elk.es_index_name = config.getini("es_index_name")
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
        try:
            return os.getlogin()
        except Exception:  # pylint: disable=broad-except
            # seems like there are case we can't get the name of the user that is currently running
            LOGGER.warning(
                "couldn't figure out which user is currently running setting to 'unknown'"
            )
            LOGGER.warning(
                "see https://docs.python.org/3/library/getpass.html#getpass.getuser, "
                "if you want to configure it correctly"
            )
            return "unknown"


class ElkReporter(object):  # pylint: disable=too-many-instance-attributes
    def __init__(self, config):
        self.es_address = config.getoption("es_address") or config.getini("es_address")
        self.es_username = config.getoption("es_username") or config.getini(
            "es_username"
        )
        self.es_password = config.getoption("es_password") or config.getini(
            "es_password"
        )
        self.es_index_name = config.getini("es_index_name")
        self.es_timeout = config.getoption("es_timeout")

        self.es_max_splice_time = config.getoption("es_max_splice_time")
        self.es_default_test_time = config.getoption("es_default_test_time")

        self.slices_query_fmt = '(name:"{}") AND (outcome: passed)'

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
                "error & error",
            ],
            0,
        )
        self.session_data = dict(username=get_username(), hostname=socket.gethostname())
        self.test_data = defaultdict(dict)
        self.reports = {}
        self.config = config

    @property
    def es_auth(self):
        return self.es_username, self.es_password

    @property
    def es_url(self):
        if self.es_address.startswith("http"):
            return "{0.es_address}".format(self)
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

    def get_worker_id(self):
        # based on https://github.com/pytest-dev/pytest-xdist/pull/505
        # (to support older version of xdist)
        worker_id = "default"
        if hasattr(self.config, "workerinput"):
            worker_id = self.config.workerinput["workerid"]
        if (
            not hasattr(self.config, "workerinput")
            and getattr(self.config.option, "dist", "no") != "no"
        ):
            worker_id = "master"
        return worker_id

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
            # in xdist, report only on worker nodes
            if self.get_worker_id() != "master":
                old_report = self.get_report(report)
                if report.passed and old_report:
                    self.report_test(old_report[0], old_report[1])
                if report.failed and old_report:
                    self.report_test(
                        report, old_report[1] + " & error", old_report=old_report[0]
                    )
                if report.skipped:
                    self.report_test(report, "skipped")

    def report_test(self, item_report, outcome, old_report=None):
        self.stats[outcome] += 1
        test_data = dict(
            item_report.user_properties,
            timestamp=datetime.datetime.utcnow().isoformat(),
            name=item_report.nodeid,
            outcome=outcome,
            duration=item_report.duration,
            markers=item_report.keywords,
            **self.session_data,
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
        self.session_data["session_start_time"] = datetime.datetime.utcnow().isoformat()

    def pytest_sessionfinish(self):
        if not self.config.getoption("collectonly"):
            test_data = dict(summery=True, stats=self.stats, **self.session_data)
            self.post_to_elasticsearch(test_data)

    def pytest_terminal_summary(self, terminalreporter):
        verbose = terminalreporter.config.getvalue("verbose")

        if not self.config.getoption("collectonly") and verbose < 2 and self.es_address:
            terminalreporter.write_sep(
                "-",
                "stats posted to elasticsearch [%s]: %s"
                % (self.es_address, self.stats),
            )

    def pytest_internalerror(self, excrepr):
        test_data = dict(
            timestamp=datetime.datetime.utcnow().isoformat(),
            outcome="internal-error",
            faiure_message=excrepr,
            **self.session_data,
        )
        self.post_to_elasticsearch(test_data)

    def post_to_elasticsearch(self, test_data):
        if self.es_address:
            try:
                url = "{0.es_url}/{0.es_index_name}/_doc".format(self)
                res = requests.post(
                    url, json=test_data, auth=self.es_auth, timeout=self.es_timeout
                )
                res.raise_for_status()
            except Exception as ex:  # pylint: disable=broad-except
                LOGGER.warning("Failed to POST to elasticsearch: [%s]", str(ex))

    def fetch_test_duration(
        self, collected_test_list, default_time_sec=120.0, max_workers=20
    ):
        """
        fetch test 95 percentile duration of a list of tests

        :param collected_test_list: the names of the test to lookup
        :param default_time_sec: the time to return when no history data found
        :param max_workers: number of threads to use for concurrency

        :returns: map from test_id to 95 percentile duration
        """

        test_durations = []
        session = requests.Session()

        def get_test_stats(test_id):
            url = "{0.es_url}/{0.es_index_name}/_search?size=0".format(self)
            body = {
                "query": {
                    "query_string": {"query": self.slices_query_fmt.format(test_id)}
                },
                "aggs": {
                    "percentiles_duration": {
                        "percentiles": {"field": "duration", "percents": [90, 95, 99]}
                    },
                },
            }
            try:
                res = session.post(
                    url, json=body, auth=self.es_auth, timeout=self.es_timeout
                )
                res.raise_for_status()
                return dict(
                    test_name=test_id,
                    duration=res.json()["aggregations"]["percentiles_duration"][
                        "values"
                    ]["95.0"],
                )
            except (requests.exceptions.ReadTimeout, requests.exceptions.HTTPError):
                return dict(test_name=test_id, duration=None)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_test_id = {
                executor.submit(get_test_stats, test_id): test_id
                for test_id in collected_test_list
            }
            for future in concurrent.futures.as_completed(future_to_test_id):
                test_id = future_to_test_id[future]
                try:
                    test_durations.append(future.result())
                except Exception:  # pylint: disable=broad-except
                    LOGGER.exception("'%s' generated an exception", test_id)

        for test in test_durations:
            if not test["duration"]:
                test["duration"] = default_time_sec
        test_durations.sort(key=lambda x: x["duration"])
        LOGGER.debug(pprint.pformat(test_durations))

        return test_durations

    @staticmethod
    def clear_old_exclude_files(outputdir):
        print("clear old exclude files")
        # Get a list of all files in directory
        for root_dir, _, filenames in os.walk(outputdir):
            # Find the files that matches the given pattern
            for filename in fnmatch.filter(filenames, "include_*.txt"):
                try:
                    os.remove(os.path.join(root_dir, filename))
                except OSError:
                    print(f"Error while deleting file {filename}")

    @staticmethod
    def split_files_test_list(outputdir, slices):
        for i, current_slice in enumerate(slices):
            print(
                f"{i}: {datetime.timedelta(0, current_slice['total'])} "
                f"- {len(current_slice['tests'])} - {current_slice['tests']}"
            )
            include_filename = os.path.join(outputdir, "include_%03d.txt" % i)

            with open(include_filename, "w") as slice_file:
                for case in current_slice["tests"]:
                    slice_file.write(case + "\n")

    @staticmethod
    def make_test_slices(test_data, max_slice_duration):
        slices = []
        while test_data:
            current_test = test_data.pop(0)
            for current_slice in slices:
                if (
                    current_slice["total"] + float(current_test["duration"])
                    > max_slice_duration
                ):
                    continue
                current_slice["total"] += float(current_test["duration"])
                current_slice["tests"] += [current_test["test_name"]]
                break
            else:
                slices += [dict(total=0.0, tests=[])]
                current_slice = slices[-1]
                current_slice["total"] += float(current_test["duration"])
                current_slice["tests"] += [current_test["test_name"]]
        return slices

    def pytest_collection_finish(self, session):

        if self.config.getoption("es_slices"):
            assert (
                self.es_default_test_time and self.es_max_splice_time
            ), "'--es-max-splice-time' and '--es-default-test-time' should be positive numbers"
            test_history_data = self.fetch_test_duration(
                [item.nodeid.replace("::()", "") for item in session.items],
                default_time_sec=self.es_default_test_time,
            )
            slices = self.make_test_slices(
                test_history_data, max_slice_duration=self.es_max_splice_time * 60
            )
            LOGGER.debug(pprint.pformat(slices))
            self.clear_old_exclude_files(outputdir=".")
            self.split_files_test_list(outputdir=".", slices=slices)


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
def github_data(request):
    """
    Append github ci job and user data into results session
    """
    if os.environ.get("GITHUB_ACTIONS", False) == "true":
        github_env = {
            k.lower(): v for k, v in os.environ.items() if k.startswith("GITHUB_")
        }

        elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
        elk.session_data.update(**github_env)


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
                subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL)
                .decode("utf-8")
                .strip()
            )
        except subprocess.CalledProcessError:
            pass
    elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
    elk.session_data.update(**git_info)
