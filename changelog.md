# Changes

## Breaking changes

## New features

## Bug fixes

- Fix the graph widget failing to render in PyCharm and VS Code
- Fix the graph widget restyling the surrounding page in Marimo notebooks

## Improvements

- Reduce the widget payload.

## Other changes

- Stop committing the built widget JS/CSS assets; they are now built by `just js-build` and in CI, and the shipped Streamlit stylesheet no longer duplicates the widget's.
- Update the GDS example notebook to the GDS client 2.x API and exercise it against the latest client in the integration tests.
