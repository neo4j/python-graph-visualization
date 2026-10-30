# Changes

## Breaking changes

* The `Layout`, `CaptionAlignment`, `Direction`, `Packing`, `Renderer`, `SelectionMode`,
  `WidgetLayout`, and `ColorSpace` enums are now `StrEnum`s: `str()` of a member (and
  f-string interpolation) returns the value (e.g. `"grid"`) instead of the member name
  (e.g. `"Layout.GRID"`).

## New features

## Bug fixes

* Avoid pandas 3.1 deprecation warnings when building a graph from GDS

## Improvements

* Support Python 3.15
* Support the GDS client 2.3

## Other changes

* Remove the `enum-tools` dependency: the `document_enum` decorator only did anything
  in interactive sessions, and the enum member docstrings are picked up from the source
  when the docs are built.
* Drop support for Python 3.10
* On Python 3.15, the `pandas` extra installs pandas 3 (pandas 2 has no 3.15 wheels)
* The `snowflake` extra is not available on Python 3.15 until `snowflake-connector-python` ships 3.15 wheels
