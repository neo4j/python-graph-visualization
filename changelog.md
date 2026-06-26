# Changes

## Breaking changes

## New features

* Added the ability to set the selection mode (gesture) of the `GraphWidget` from Python, via the `selection_mode` render option or the `GraphWidget.set_selection_mode` method.
* Added the `GraphWidget.selected` trait to read back the IDs of the nodes and relationships selected in the widget UI. Use the `GraphWidget.on_selection_change` method (or `widget.observe`) to react to selection changes.

## Bug fixes

## Improvements

## Other changes
