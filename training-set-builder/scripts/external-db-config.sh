# #!/usr/bin/env bash

# ENV_FILE=".env"

# if [ -f "$ENV_FILE" ]; then
#     . $PWD/$ENV_FILE
# else
#     echo "'$ENV_FILE' could not be found. See Readme on how to set up."
#     exit 1
# fi

# CONFIG_PATH=$1
# NAME=external-database
# KEYS=(hostname name password username role)
# VALUES=(
#     $PG_HOST
#     $PG_NAME
#     $PG_PWD
#     $PG_USER
#     $PG_ROLE
# )

# mkdir -p "$CONFIG_PATH/$NAME" > /dev/null 2>&1

# for i in "${!KEYS[@]}"; do
#   echo ${VALUES[$i]} > "$CONFIG_PATH/$NAME/${KEYS[$i]}"
# done
