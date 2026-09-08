# Client configuration

This guide covers the configuration options for the product client library.

## Timeouts

The default request timeout is 30 seconds. You can override it by setting
`RequestTimeout` on the `Config` struct before creating a client.

## Retries

The client retries up to 3 times before giving up. Retries use exponential
backoff.

## Pagination

The `list_items` endpoint returns 20 items per page by default. The maximum
page size is 100; requesting more raises an error.

## Design notes

We designed the client to be simple to reason about, which is why the
configuration surface is deliberately small. Future releases may add more
options.

See the API reference for the full list of methods.
