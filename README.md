# pytest-elk-reporter

[![PyPI version](https://img.shields.io/pypi/v/pytest-elk-reporter.svg?style=flat)](https://pypi.org/project/pytest-elk-reporter)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-elk-reporter.svg?style=flat)](https://pypi.org/project/pytest-elk-reporter)
![.github/workflows/tests.yml](https://github.com/fruch/pytest-elk-reporter/workflows/.github/workflows/tests.yml/badge.svg)
[![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/fruch/pytest-elk-reporter.svg?style=flat)](https://libraries.io/github/fruch/pytest-elk-reporter)
[![Using Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![Codecov Reports](https://codecov.io/gh/fruch/pytest-elk-reporter/branch/master/graph/badge.svg)](https://codecov.io/gh/fruch/pytest-elk-reporter)

A plugin to send pytest test results to [ELK] stack, with extra context data

## Features

* Reporting into Elasticsearch each test result, as the test finish
* Automaticlly append context data to each test:
  * git inforamtion such as `branch` or `last commit` and more
  * all of Jenkins env variables
  * username if available
* Report a test summery to Elastic for each session with all the context data
* can append any user data into the context sent to elastic

## Requirements

* having [pytest] tests written

## Installation

You can install "pytest-elk-reporter" via [pip] from [PyPI]

``` bash
pip install pytest-elk-reporter
```

### ElasticSearch configureation

We need this auto_create_index enable for the indexes that are going to be used,
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

For more info on this elasticsearch feature check thier [index documention](https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-index_.html#index-creation)

## Usage

### Run and configure from command line

```bash
pytest --es-address 127.0.0.1:9200
# or if you need user/password to authenticate
pytest --es-address my-elk-server.io:9200 --es-username fruch --es-password 'passwordsarenicetohave'
```

### Configure from code (Idealy in conftest.py)

```python
import pytest

@pytest.fixture(scope='session', autouse=True)
def configure_es(elk_reporter):
    # TODO: get cerdentials in more secure fashion programtically, maybe AWS secrects or the likes
    # or put them in plain-text in the code... what can ever go wrong...
    elk_reporter.es_address = "my-elk-server.io:9200"
    elk_reporter.es_user = 'fruch'
    elk_reporter.es_password = 'passwordsarenicetohave'
    elk_reporter.es_index_name = 'test_data'

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
for more about how to configure using .ini files

### Collect context data for the whole session

For example, with this I'll be able to build a dash board per version

```python
@pytest.fixture(scope="session", autouse=True)
def report_formal_version_to_elk(request):
    """
    Append my own data specific, for example which of the code uner test is used
    """
    # TODO: take it programticly of of the code under test...
    my_data = {"formal_version": "1.0.0-rc2" }

    elk = request.config.pluginmanager.get_plugin("elk-reporter-runtime")
    elk.session_data.update(**my_data)
```

### Collect data for specific tests

```python
def test_my_service_and_collect_timings(request, elk_reporter):
    response = requests.get("http://my-server.io/api/do_something")
    assert response.status_code == 200

    elk_reporter.append_test_data(request, {"do_something_response_time": response.elapsed.total_seconds() })
    # now doing response time per version dashboard quite easy
    # and yeah, it's not exactly real usable metric, it's just an example...
```

## Contributing

Contributions are very welcome. Tests can be run with [`tox`][tox], please ensure
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
