# Changes

## Breaking changes

## New features

## Bug fixes

* Fixed a stored cross-site scripting (XSS) vulnerability in `VG.render()`. Graph data was injected into an executable `<script>` block, so a node caption or property value containing `</script>` could break out and run arbitrary code in the browser of anyone opening a saved visualization. Data is now delivered as an inert `<script type="application/json">` block and read back with `JSON.parse`, with `<` escaped so no `</script>` can appear literally. The `render_widget` was unaffected.

## Improvements

## Other changes
