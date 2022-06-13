export CONFIG_PATH=./configmaps

ENV_FILE=${1:-".env"}

if [ -f "$ENV_FILE" ]; then
    . $PWD/$ENV_FILE
else
    echo "'$ENV_FILE' could not be found. See Readme on how to set up."
    exit 1
fi

# Run the application
./bin/${APP:-"main"}
