#!/bin/bash

# set environment variables from .env file for the script to authenticate using service principal
# Load environment variables from .env file
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  export $(grep -v '^#' .env | xargs)
else
  echo ".env file not found."
  exit 1
fi

# install niet if not installed
if ! command -v niet &> /dev/null; then
  echo "Installing niet..."
  pip install niet
fi


# Navigate to the directory of the script
cd "$(dirname "$0")"
# Load variables from YAML file using niet
config_file="config.yaml"


# Read arguments from config.yaml
StorageAccountName=$(niet "variables.StorageAccountName" $config_file)
StorageAccountUrl=$(niet "variables.StorageAccountUrl" $config_file)
ContainerName=$(niet "variables.ContainerName" $config_file)
SearchEndpoint=$(niet "variables.SearchEndpoint" $config_file)
IndexName=$(niet "variables.IndexName" $config_file)

# check if the initialsation of all the variables is successful
if [ -z "$StorageAccountName" ] || [ -z "$StorageAccountUrl" ] || [ -z "$ContainerName" ] || [ -z "$SearchEndpoint" ] || [ -z "$IndexName" ]; then
  echo "Failed to load variables from config file."
  exit 1
fi

# Navigate to the indexer directory
cd ../indexer || { echo "Failed to navigate to indexer directory"; exit 1; }

# Run the Python script with the arguments
echo "Resetting index..."
python reset_index.py \
 --storage-account-url "$StorageAccountUrl" \
 --container-name "$ContainerName" \
 --search-service-endpoint "$SearchEndpoint" \
 --index-name "$IndexName" \
 --verbose

 # display success message only if above steps are successful
if [ $? -eq 0 ]; then
  echo "Index reset successfully."
else
  echo "Failed to reset index."
fi

