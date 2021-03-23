# pytest-elk-reporter

[![PyPI version](https://img.shields.io/pypi/v/pytest-elk-reporter.svg?style=flat)](https://pypi.org/project/pytest-elk-reporter)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-elk-reporter.svg?style=flat)](https://pypi.org/project/pytest-elk-reporter)
[![.github/workflows/tests.yml](https://github.com/fruch/pytest-elk-reporter/workflows/.github/workflows/tests.yml/badge.svg)](https://github.com/fruch/pytest-elk-reporter/actions?query=branch%3Amaster)
[![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/fruch/pytest-elk-reporter.svg?style=flat)](https://libraries.io/github/fruch/pytest-elk-reporter)
[![Using Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![Codecov Reports](https://codecov.io/gh/fruch/pytest-elk-reporter/branch/master/graph/badge.svg)](https://codecov.io/gh/fruch/pytest-elk-reporter)

A plugin to send pytest test results to [ELK] stack, with extra context data

## Features

* Report each test result into Elasticsearch as they finish
* Automatically append contextual data to each test:
  * git information such as `branch` or `last commit` and more
  * all of CI env variables
    * Jenkins
    * Travis
    * Circle CI
    * Github Actions
  * username if available
* Report a test summary to Elastic for each session with all the context data
* Append any user data into the context sent to Elastic

## Requirements

* having [pytest] tests written

## Installation

You can install "pytest-elk-reporter" via [pip] from [PyPI]

``` bash
pip install pytest-elk-reporter
```

### Elasticsearch configuration

We need this `auto_create_index` setting enabled for the indexes that are going to be used,
since we don't have code to create the indexes, this is the default

```bash
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
{
    "persistent": {
        "action.auto_create_index": "true"
    }
}
'
```

For more info on this Elasticsearch feature check their [index documention](https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-index_.html#index-creation)

## Usage

### Run and configure from command line

```bash
pytest --es-address 127.0.0.1:9200
# or if you need user/password to authenticate
pytest --es-address my-elk-server.io:9200 --es-username fruch --es-password 'passwordsarenicetohave'
```

### Configure from code (ideally in conftest.py)

```python
from pytest_elk_reporter import ElkReporter

def pytest_plugin_registered(plugin, manager):
    if isinstance(plugin, ElkReporter):
      # TODO: get credentials in more secure fashion programmatically, maybe AWS secrets or the likes
      # or put them in plain-text in the code... what can ever go wrong...
      plugin.es_address = "my-elk-server.io:9200"
      plugin.es_user = 'fruch'
      plugin.es_password = 'passwordsarenicetohave'
      plugin.es_index_name = 'test_data'

```

### Configure from pytest ini file

```ini
# put this in pytest.ini / tox.ini / setup.cfg
[pytest]
es_address = my-elk-server.io:9200
es_user = fruch
es_password = passwordsarenicetohave
es_index_name = test_data
```

see [pytest docs](https://docs.pytest.org/en/latest/customize.html)
for more about how to configure pytest using .ini files

### Collect context data for the whole session

In this example, I'll be able to build a dashboard for each version:

```python
import pytest

@pytest.fixture(scope="session", autouse=True)
def report_formal_version_to_elk(request):
    """
    Append my own data specific, for example which of the code under test is used
    """
    # TODO: programmatically set to the version of the code under test...
    my_data = {"formal_version": "1.0.0-rc2" }

    elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
    elk.session_data.update(**my_data)
```

### Collect data for specific tests


```python
import requests

def test_my_service_and_collect_timings(request, elk_reporter):
    response = requests.get("http://my-server.io/api/do_something")
    assert response.status_code == 200

    elk_reporter.append_test_data(request, {"do_something_response_time": response.elapsed.total_seconds() })
    # now, a dashboard showing response time by version should be quite easy
    # and yeah, it's not exactly a real usable metric, but it's just one example...
```

Or via the `record_property` built-in fixture (that is normally used to collect data into junit.xml reports):

```python
import requests

def test_my_service_and_collect_timings(record_property):
    response = requests.get("http://my-server.io/api/do_something")
    assert response.status_code == 200

    record_property("do_something_response_time", response.elapsed.total_seconds())
```

## Split tests based on their duration histories

One cool thing that can be done now that you have a history of the tests,
is to split the tests based on their actual runtime when passing.
For long-running integration tests, this is priceless.

In this example, we're going to split the run into a maximum of 4 min slices.
Any test that doesn't have history information is assumed to be 60 sec long.

```bash
# pytest --collect-only --es-splice --es-max-splice-time=4 --es-default-test-time=60
...

0: 0:04:00 - 3 - ['test_history_slices.py::test_should_pass_1', 'test_history_slices.py::test_should_pass_2', 'test_history_slices.py::test_should_pass_3']
1: 0:04:00 - 2 - ['test_history_slices.py::test_with_history_data', 'test_history_slices.py::test_that_failed']

...

# cat include000.txt
test_history_slices.py::test_should_pass_1
test_history_slices.py::test_should_pass_2
test_history_slices.py::test_should_pass_3

# cat include000.txt
test_history_slices.py::test_with_history_data
test_history_slices.py::test_that_failed

### now we can run each slice on its own machine
### on machine1
# pytest $(cat include000.txt)

### on machine2
# pytest $(cat include001.txt)
```

## Contributing

Contributions are very welcome. Tests can be run with [`tox`][tox]. Please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT][MIT] license, "pytest-elk-reporter" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

## Thanks

This [pytest] plugin was generated with [Cookiecutter] along with [@hackebrot]'s [cookiecutter-pytest-plugin] template.

[ELK]: https://www.elastic.co/elk-stack
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@hackebrot]: https://github.com/hackebrot
[MIT]: http://opensource.org/licenses/MIT
[cookiecutter-pytest-plugin]: https://github.com/pytest-dev/cookiecutter-pytest-plugin
[file an issue]: https://github.com/fruch/pytest-elk-reporter/issues
[pytest]: https://github.com/pytest-dev/pytest
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/project
