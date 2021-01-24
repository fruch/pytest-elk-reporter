def test_xdist(testdir):  # pylint: disable=redefined-outer-name
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

    result = testdir.runpytest("--es-address=127.0.0.1:9200", "-s", "-v", "-n", "2")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*PASSED*test_xdist.py::test_1 "])
    result.stdout.fnmatch_lines(["*PASSED*test_xdist.py::test_2 "])


def test_without_xdist(testdir):  # pylint: disable=redefined-outer-name
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

    result = testdir.runpytest(
        "--es-address=127.0.0.1:9200", "-s", "-v", "-p", "no:xdist"
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["test_without_xdist.py::test_1*PASSED"])
    result.stdout.fnmatch_lines(["test_without_xdist.py::test_2*PASSED"])
