# -*- coding: utf-8 -*-

import os
import json

import pytest


def test_failures(testdir, requests_mock):  # pylint: disable=redefined-outer-name
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture
        def failed_fixture():
            assert False

        def test_fail():
            assert False

        def test_failed_fixture(failed_fixture):
            pass

        @pytest.mark.skip(reason="no way of currently testing this")
        def test_skip():
            pass

        def test_skip_during_test():
            pytest.skip("unsupported configuration")

        @pytest.mark.xfail(strict=True)
        def test_xfail():
            raise Exception("this test should fail")

        @pytest.mark.xfail()
        def test_xpass():
            pass

        @pytest.mark.xfail(strict=True)
        def test_xpass_strict():
            pass

        @pytest.fixture()
        def fail_teardown(request):
            def fin():
                raise Exception("teardown failed")
            request.addfinalizer(fin)

        def test_failure_in_fin(fail_teardown):
            pass

        def test_failure_in_fin_2(fail_teardown):
            raise Exception("failed inside test")

        def test_failure_in_fin_3(fail_teardown):
            pytest.skip("skip form test")

        @pytest.fixture()
        def skip_in_teardown(request):
            def fin():
                pytest.skip("skip form test")
            request.addfinalizer(fin)

        def test_skip_in_teardown(skip_in_teardown):
            pass

        def test_failing_subtests(subtests):
            with subtests.test("failed subtest"):
                raise Exception("should fail")
            with subtests.test("succcess subtest"):
                pass

    """
    )

    # run pytest with the following cmd args
    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_fail FAILED*"])
    result.stdout.fnmatch_lines(["*::test_failed_fixture ERROR*"])
    result.stdout.fnmatch_lines(["*::test_xfail XFAIL*"])
    result.stdout.fnmatch_lines(["*::test_xpass XPASS*"])
    result.stdout.fnmatch_lines(["*::test_xpass_strict FAILED*"])

    result.stdout.fnmatch_lines(["*::test_skip SKIPPED*"])
    result.stdout.fnmatch_lines(["*::test_skip_during_test SKIPPED*"])

    result.stdout.fnmatch_lines(["*::test_failure_in_fin ERROR*"])
    result.stdout.fnmatch_lines(["*::test_failure_in_fin_2 FAILED*"])
    result.stdout.fnmatch_lines(["*::test_failure_in_fin_3 ERROR*"])

    # make sure that we get a '1' exit code for the testsuite
    assert result.ret == 1

    last_report = json.loads(requests_mock.request_history[-1].text)
    assert last_report["stats"] == {
        "error": 1,
        "failure": 3,
        "failure & error": 1,
        "passed": 2,
        "skipped & error": 1,
        "passed & error": 1,
        "skipped": 4,
        "xfailed": 1,
        "xpass": 1,
        "error & error": 0,
    }


@pytest.mark.this_marker
def test_es_configuration(testdir):
    """Make sure that pytest accepts our elasticsearch configuration."""

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        from pytest_elk_reporter import ElkReporter
        def test_sth(elk_reporter):
            assert isinstance(elk_reporter, ElkReporter)

    """
    )

    # run pytest with the following cmd args
    result = testdir.runpytest(
        "--es-address=127.0.0.1:9200",
        "--es-username=fruch",
        "--es-password=none",
        "-v",
        "-s",
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_sth PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_bad_es_configuration(testdir):
    """Make sure that pytest accepts our elasticsearch configuration."""

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        from pytest_elk_reporter import ElkReporter
        def test_sth(elk_reporter):
            assert isinstance(elk_reporter, ElkReporter)

    """
    )

    # run pytest with the following cmd args
    result = testdir.runpytest("--es-address=12452456:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_sth PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_help_message(testdir):
    result = testdir.runpytest("--help")
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["elk-reporter:", "*--es-address=ES_ADDRESS*"])


def test_jenkins_env_collection(testdir):
    os.environ["JENKINS_USERNAME"] = "Israel Fruchter"

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_collection_elk(elk_reporter):
            assert elk_reporter.session_data['jenkins_username'] == 'Israel Fruchter'
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_collection_elk PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_travis_env_collection(testdir):
    os.environ["TRAVIS"] = "true"
    os.environ["TRAVIS_USERNAME"] = "Israel Fruchter"

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_collection_elk(elk_reporter):
            assert elk_reporter.session_data['travis_username'] == 'Israel Fruchter'
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_collection_elk PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_circle_env_collection(testdir):
    os.environ["CIRCLECI"] = "true"
    os.environ["CIRCLE_USERNAME"] = "Israel Fruchter"

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_collection_elk(elk_reporter):
            assert elk_reporter.session_data['circle_username'] == 'Israel Fruchter'
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_collection_elk PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_github_env_collection(testdir):
    os.environ["GITHUB_ACTIONS"] = "true"
    os.environ["GITHUB_ACTOR"] = "Israel Fruchter"

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_collection_elk(elk_reporter):
            assert elk_reporter.session_data['github_actor'] == 'Israel Fruchter'
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_collection_elk PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_setup_es_from_code(testdir, requests_mock):
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture(scope='session', autouse=True)
        def configure_es(elk_reporter):
            elk_reporter.es_address = "127.0.0.1:9200"
            elk_reporter.es_username = 'test'
            elk_reporter.es_password = 'mypassword'
            elk_reporter.es_index_name = 'test_data'

        def test_should_pass():
            pass
        """
    )

    result = testdir.runpytest("-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_should_pass PASSED*"])
    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
    auth_header = requests_mock.request_history[-1].headers.get("Authorization")
    assert "Basic" in auth_header


def test_setup_es_api_key_from_code(testdir, requests_mock):
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture(scope='session', autouse=True)
        def configure_es(elk_reporter):
            elk_reporter.es_address = "127.0.0.1:9200"
            elk_reporter.es_api_key = 'VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw=='
            elk_reporter.es_index_name = 'test_data'

        def test_should_pass():
            pass
        """
    )

    result = testdir.runpytest("-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_should_pass PASSED*"])
    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0

    auth_header = requests_mock.request_history[-1].headers.get("Authorization")
    assert "ApiKey" in auth_header


def test_git_info(testdir, requests_mock):  # pylint: disable=redefined-outer-name

    # create a fake git repo
    testdir.run("git", "init")
    testdir.run("git", "checkout", "-b", "master")
    testdir.run(
        "git", "remote", "add", "origin", "http://github.com/something/something.git"
    )
    testdir.run("touch", "README.md")
    testdir.run("git", "add", "README.md")
    testdir.run("git", "config", "user.name", '"Your Name"')
    testdir.run("git", "config", "user.email", '"something@gmail.com"')
    testdir.run("git", "commit", "-a", "-m", "'initial commit'")

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_should_pass():
            pass
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_should_pass PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    last_report = json.loads(requests_mock.request_history[-1].text)
    assert last_report["git_branch"] == "master"
    assert "initial commit" in last_report["git_commit_oneline"]
    assert "initial commit" in last_report["git_commit_full"]
    assert "git_commit_sha" in last_report
    assert "git_commit_sha_short" in last_report
    assert last_report["git_repo"] == "http://github.com/something/something.git"


def test_append_test_data(
    testdir, requests_mock
):  # pylint: disable=redefined-outer-name
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_1(request, elk_reporter):
            elk_reporter.append_test_data(request, {"my_key": 1})
        def test_2():
            pass
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_1 PASSED*"])
    result.stdout.fnmatch_lines(["*::test_2 PASSED*"])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    first_report = json.loads(requests_mock.request_history[0].text)
    assert first_report["my_key"] == 1

    second_report = json.loads(requests_mock.request_history[1].text)
    assert "my_key" not in second_report, "key should be only on specific test"


def test_setup_es_from_ini(testdir):
    # create a temporary pytest test module
    testdir.makeini(
        """
        [pytest]
        es_address = my_own_es_address
        es_index_name = my_own_index
        """
    )
    testdir.makepyfile(
        """
        def test_should_pass(elk_reporter):
            assert elk_reporter.es_index_name == 'my_own_index'
            assert elk_reporter.es_address == 'my_own_es_address'
        """
    )

    result = testdir.runpytest("-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_should_pass PASSED*"])
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_marker_collection(
    testdir, requests_mock
):  # pylint: disable=redefined-outer-name
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.mark1
        def test_1(request):
            pass

        @pytest.mark.mark2
        def test_2():
            pass
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_1 PASSED*"])
    result.stdout.fnmatch_lines(["*::test_2 PASSED*"])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    first_report = json.loads(requests_mock.request_history[0].text)
    assert "mark1" in first_report["markers"]

    second_report = json.loads(requests_mock.request_history[1].text)
    assert "mark2" in second_report["markers"]


def test_user_properties(
    testdir, requests_mock
):  # pylint: disable=redefined-outer-name
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        def test_1(record_property):
            record_property("example_key", 1)
            pass
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_1 PASSED*"])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    report = json.loads(requests_mock.request_history[0].text)
    assert "example_key" in report
    assert report["example_key"] == 1


def test_marks(testdir, requests_mock):  # pylint: disable=redefined-outer-name
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        pytestmark = [pytest.mark.module_level]

        @pytest.mark.class_level
        class TestClass:

            @pytest.mark.method_level
            def test_1(record_property):
                pass
        """
    )

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-s", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_1 PASSED*"])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    report = json.loads(requests_mock.request_history[0].text)
    assert set(report["markers"]) == {"module_level", "class_level", "method_level"}


def test_post_reports(testdir, requests_mock):  # pylint: disable=redefined-outer-name
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        def test_1(elk_reporter):
            assert elk_reporter.es_post_reports
        """
    )

    result = testdir.runpytest(
        "--es-address=127.0.0.1:9200", "--es-post-reports", "-s", "-v"
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_1 PASSED*"])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    assert (
        requests_mock.called
    ), "Requests are made to Elasticsearch when es_post_reports is True"


def test_no_post_reports(
    testdir, requests_mock
):  # pylint: disable=redefined-outer-name
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        def test_1(elk_reporter):
            assert not elk_reporter.es_post_reports
        """
    )

    result = testdir.runpytest(
        "--es-address=127.0.0.1:9200", "--es-no-post-reports", "-s", "-v"
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_1 PASSED*"])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0

    assert (
        not requests_mock.called
    ), "Requests are not made to Elasticsearch when es_post_reports is False"


def test_subtests(testdir, requests_mock):  # pylint: disable=redefined-outer-name
    """Make sure subtests are identified and reported."""

    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        def test_failing_subtests(subtests):
            with subtests.test("failed subtest"):
                raise Exception("should fail")
            with subtests.test("success subtest"):
                pass

    """
    )
    # run pytest with the following cmd args
    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_failing_subtests * SUBFAIL*"])
    result.stdout.fnmatch_lines(["*::test_failing_subtests * SUBPASS*"])
    result.stdout.fnmatch_lines(["*::test_failing_subtests PASSED*"])

    # make sure that that we get a '1' exit code for the testsuite
    assert result.ret == 1

    # validate each subtest is being reported on its own
    report = json.loads(requests_mock.request_history[-2].text)
    assert report["name"] == "test_subtests.py::test_failing_subtests"
    assert "subtest" not in report
    assert report["outcome"] == "passed"

    report = json.loads(requests_mock.request_history[-3].text)
    assert report["name"] == "test_subtests.py::test_failing_subtests"
    assert report["subtest"] == "success subtest"
    assert report["outcome"] == "passed"

    report = json.loads(requests_mock.request_history[-4].text)
    assert report["name"] == "test_subtests.py::test_failing_subtests"
    assert report["subtest"] == "failed subtest"
    assert report["outcome"] == "failure"
