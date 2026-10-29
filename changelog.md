# Changes

## Breaking changes

## New features

## Bug fixes

* Avoid pandas 3.1 deprecation warnings when building a graph from GDS

## Improvements

* Support Python 3.15
* Support the GDS client 2.3

## Other changes

* Drop support for Python 3.10
* On Python 3.15, the `pandas` extra installs pandas 3 (pandas 2 has no 3.15 wheels)
* The `snowflake` extra is not available on Python 3.15 until `snowflake-connector-python` ships 3.15 wheels
