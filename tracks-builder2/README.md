# AIS DB Updater

> Updates an external DB with extracts from the MaritimeOptima AIS DB

## Config

Firstly, you need to provide the desired external database where the data
will be copied to in a `.env` file with the following variables exposed:

```env
# External DB config
PG_HOST   # {string} PostgreSQL database host
PG_NAME   # {string} PostgreSQL database name
PG_USER   # {string} PostgreSQL database username
PG_PWD    # {string} PostgreSQL database password
PG_ROLE   # {string} PostgreSQL database role
```

To provide the program with correct environment variables run `make configmaps`
or `make -B configmaps` to override existing data.

For this to work you need to be connected to MaritimeOptima's dev or core cluster.

## Commands

(See `Makefile` for more info)

### `make run`

Creates binary and runs program with values from `.env` file sourced.

### `make lint`

Runs `golangci-lint run` with `.golangci.yml` config file.

### `make dev`

Builds binary.

### `make bin`

Creates binary ready to be used by Docker image.

### `make build`

Builds Docker image.
