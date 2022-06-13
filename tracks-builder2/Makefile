VERSION?="0.0.1"
TEST?=./...
DOCKER_REPO="maritimeoptima.azurecr.io/voyage-predictions/tracks-builder"
NAME="tracks-builder"
COMMIT=$(shell git rev-parse --short HEAD)
BRANCH=$(shell git rev-parse --abbrev-ref HEAD)
CONFIG_PATH=./configmaps

default: run

# bin generates the releaseable binary for users
bin:
	@MO_RELEASE=1 sh -c "'$(CURDIR)/scripts/build.sh'"

lint:
	golangci-lint run

quickdev:
	@sh -c "'$(CURDIR)/scripts/build.sh'"

run: quickdev
	@sh -c "'$(CURDIR)/scripts/dev.sh'"

.NOTPARALLEL:

.PHONY: bin configmaps default lint quickdev bin run build release remote
