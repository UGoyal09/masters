#!/usr/bin/env bash

#
# Usage:
#   ../scripts/put-secret.bash <config-path> <name> <key>
#
# Example:
#   ../scripts/put-secret.bash $(CONFIG_PATH) vessels-database hostname
#

CONFIG_PATH=$1
NAME=$2
KEY=$3

mkdir -p "$CONFIG_PATH/$NAME" > /dev/null 2>&1

kubectl get secret \
    -n services $NAME \
    -o jsonpath="{.data.$KEY}" | base64 -d \
    > "$CONFIG_PATH/$NAME/$KEY"

