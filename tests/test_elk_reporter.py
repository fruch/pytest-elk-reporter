# -*- coding: utf-8 -*-


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
    """
    )

    # run pytest with the following cmd args
    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_fail FAILED*"])
    result.stdout.fnmatch_lines(["*::test_failed_fixture ERROR*"])
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
