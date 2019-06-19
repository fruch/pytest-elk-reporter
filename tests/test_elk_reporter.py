# -*- coding: utf-8 -*-

import os


def test_failures(testdir):
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

        @pytest.fixture()
        def fail_teardown(request):
            def fin():
                raise Exception("teardown failed")
            request.addfinalizer(fin)

        def test_failure_in_fin(fail_teardown):
            pass
    """
    )

    # run pytest with the following cmd args
    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_fail FAILED*"])
    result.stdout.fnmatch_lines(["*::test_failed_fixture ERROR*"])
    result.stdout.fnmatch_lines(["*::test_xfail XFAIL*"])

    result.stdout.fnmatch_lines(["*::test_skip SKIPPED*"])
    result.stdout.fnmatch_lines(["*::test_skip_during_test SKIPPED*"])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 1


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
    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_sth PASSED*"])
    # make sure that that we get a '0' exit code for the testsuite
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
    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_setup_es_from_code(testdir):
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture(scope='session', autouse=True)
        def configure_es(elk_reporter):
            elk_reporter.es_address = "127.0.0.1:9200"
            elk_reporter.es_user = None
            elk_reporter.es_password = None

        def test_should_pass():
            pass
        """
    )

    result = testdir.runpytest("-v", "-s")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_should_pass PASSED*"])
    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
