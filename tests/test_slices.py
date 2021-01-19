def test_history_slices(testdir):
    # create a temporary pytest test module
    testdir.makepyfile(
        """
        def test_should_pass_1(elk_reporter):
            pass
        def test_should_pass_2(elk_reporter):
            pass
        def test_should_pass_3(elk_reporter):
           pass
        def test_with_history_data(elk_reporter):
           pass
        def test_that_failed(elk_reporter):
           pass
        """
    )

    result = testdir.runpytest(
        "-v",
        "-s",
        "--collect-only",
        "--es-slices",
        "--es-max-splice-time=4",
        "--es-address=127.0.0.1:9200",
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*Function test_should_pass_1*"])
    assert "test_history_slices.py::test_that_failed" in str(result.stdout)

    # expect two specific slices
    result.stdout.fnmatch_lines(["*0: 0:04:00*"])
    result.stdout.fnmatch_lines(["*1: 0:04:00*"])
    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0

    # corresponding slice files, should exist
    with open(testdir.tmpdir / "include_000.txt") as slice_file:
        test_set_one = set(slice_file.read().splitlines())

    with open(testdir.tmpdir / "include_001.txt") as slice_file:
        test_set_two = set(slice_file.read().splitlines())

    assert test_set_one | test_set_two == {
        "test_history_slices.py::test_should_pass_1",
        "test_history_slices.py::test_should_pass_2",
        "test_history_slices.py::test_should_pass_3",
        "test_history_slices.py::test_with_history_data",
        "test_history_slices.py::test_that_failed",
    }

    # run again, to make sure we clean old include*.txt files
    result = testdir.runpytest(
        "-v",
        "-s",
        "--collect-only",
        "--es-slices",
        "--es-max-splice-time=4",
        "--es-address=127.0.0.1:9200",
    )
