# Changes

## Breaking changes

## New features

## Bug fixes

* Multiple `VG.render()` calls on one page (e.g. several notebook cells) no longer all display the first graph.
* `GraphWidget.save()` no longer times out intermittently when it is called right after the
  widget is displayed: the request now waits for the frontend to finish rendering instead of
  racing it.

## Improvements

## Other changes
