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

# # Authenticate using service principal
# echo "Authenticating with Azure using service principal..."
# az login --service-principal -u "$AZURE_CLIENT_ID" -p "$AZURE_CLIENT_SECRET" --tenant "$AZURE_TENANT_ID"
# if [ $? -ne 0 ]; then
#   echo "Error: Azure authentication failed."
#   exit 1
# fi

# install niet if not installed
if ! command -v niet &>/dev/null; then
  echo "Installing niet..."
  pip install niet
fi

# Navigate to the directory of the script
cd "$(dirname "$0")"
# Load variables from YAML file using niet
config_file="config.yaml"

StorageAccountName=$(niet "variables.StorageAccountName" $config_file)
StorageAccountUrl=$(niet "variables.StorageAccountUrl" $config_file)
ContainerName=$(niet "variables.ContainerName" $config_file)
AzureOpenAiEndpoint=$(niet "variables.AzureOpenAiEndpoint" $config_file)
AzureOpenAiEmbeddingDeploymentName=$(niet "variables.AzureOpenAiEmbeddingDeploymentName" $config_file)
AzureOpenAiModelName=$(niet "variables.AzureOpenAiModelName" $config_file)
AzureOpenAiModelDimensions=$(niet "variables.AzureOpenAiModelDimensions" $config_file)
AzureAIServicesEndpoint=$(niet "variables.AzureAIServicesEndpoint" $config_file)
SearchEndpoint=$(niet "variables.SearchEndpoint" $config_file)
IndexName=$(niet "variables.IndexName" $config_file)
TestQuery=$(niet "variables.TestQuery" $config_file)
IndexerInterval=$(niet "variables.IndexerInterval" $config_file)
SubscriptionId=$(niet "variables.SubscriptionId" $config_file)
ResourceGroupName=$(niet "variables.ResourceGroupName" $config_file)
use_ocr=$(niet "variables.use_ocr" $config_file)
use_document_layout=$(niet "variables.use_document_layout" $config_file)

# check if the initialsation of all the variables is successful
if [ -z "$StorageAccountName" ] || [ -z "$StorageAccountUrl" ] || [ -z "$ContainerName" ] || [ -z "$AzureOpenAiEndpoint" ] || [ -z "$AzureOpenAiEmbeddingDeploymentName" ] || [ -z "$AzureOpenAiModelName" ] || [ -z "$SearchEndpoint" ] || [-z "$AzureAIServicesEndpoint"] || [ -z "$IndexName" ] || [ -z "$TestQuery" ] || [ -z "$IndexerInterval" ] || [ -z "$SubscriptionId" ] || [ -z "$ResourceGroupName" ]; then
  echo "Failed to load variables from config file."
  exit 1
fi

# # Conda environment name
# CONDA_ENV_NAME="condaragsearchpoc_env"

# # Step 1: Set up Conda environment
# echo "Setting up Conda environment..."

# # Check if the environment already exists
# if conda info --envs | grep -q "$CONDA_ENV_NAME"; then
#   echo "Conda environment '$CONDA_ENV_NAME' already exists. Activating it..."
# else
#   echo "Creating Conda environment '$CONDA_ENV_NAME' with Python 3.10..."
#   conda create -name "$CONDA_ENV_NAME" python=3.10
# fi

# # Activate the Conda environment
# # source "$(conda info --base)/etc/profile.d/conda.sh"
# conda activate "$CONDA_ENV_NAME"

# # Step 2: Install requirements
# echo "Installing requirements..."
# cd ../indexer || exit
# pip install -r requirements.txt

# step 3: check if use_ocr is enabled or use_document_layout is enabled. Both can't be enabled at the same time
if [ "$use_ocr" = "True" ] && [ "$use_document_layout" = "True" ]; then
  echo "Both use_ocr and use_document_layout can't be enabled at the same time. Please enable only one of them."
  exit 1
elif [ "$use_ocr" = "True" ] && [ "$use_document_layout" = "False" ]; then
  echo "use_ocr is enabled."
elif [ "$use_document_layout" = "True" ] && [ "$use_ocr" = "False" ]; then
  echo "use_document_layout is enabled."
else
  echo "use_ocr and use_document_layout are disabled."
fi

# Step 3: Deploy datasource
echo "Deploying datasource..."
az account set --subscription "$SubscriptionId"

# Navigate to the directory of the script
cd ../indexer || exit

# Step 3: Deploy datasource
echo "Deploying datasource..."
az account set --subscription "$SubscriptionId"
python datasource.py \
  --search-endpoint "$SearchEndpoint" \
  --index-name "$IndexName" \
  --subscription-id "$SubscriptionId" \
  --resource-group-name "$ResourceGroupName" \
  --storage-account-name "$StorageAccountName" \
  --storage-account-url "$StorageAccountUrl" \
  --container-name "$ContainerName" \
  --verbose

# Step 4: Deploy index
echo "Deploying index..."
# add page numbers if use_ocr is enabled
if [ "$use_ocr" = "True" ]; then
  echo "use_ocr is enabled."
  python index.py \
    --search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --azure-openai-endpoint "$AzureOpenAiEndpoint" \
    --azure-openai-embedding-deployment-name "$AzureOpenAiEmbeddingDeploymentName" \
    --azure-openai-model-name "$AzureOpenAiModelName" \
    --azure-openai-model-dimensions "$AzureOpenAiModelDimensions" \
    --add-page-numbers \
    --verbose
elif [ "$use_document_layout" = "True" ]; then
  echo "use_document_layout is enabled."
  python index.py \
    --search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --azure-openai-endpoint "$AzureOpenAiEndpoint" \
    --azure-openai-embedding-deployment-name "$AzureOpenAiEmbeddingDeploymentName" \
    --azure-openai-model-name "$AzureOpenAiModelName" \
    --azure-openai-model-dimensions "$AzureOpenAiModelDimensions" \
    --use-document-layout \
    --verbose
else
  python index.py \
    --search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --azure-openai-endpoint "$AzureOpenAiEndpoint" \
    --azure-openai-embedding-deployment-name "$AzureOpenAiEmbeddingDeploymentName" \
    --azure-openai-model-name "$AzureOpenAiModelName" \
    --azure-openai-model-dimensions "$AzureOpenAiModelDimensions" \
    --verbose
fi

# Step 5: Deploy skillset
echo "Deploying skillset..."
# check if use_ocr is enabled or use_document_layout is enabled and pass the appropriate flag
if [ "$use_ocr" = "True" ]; then
  echo "use_ocr is enabled."
  python skillset.py \
    --azure-openai-endpoint "$AzureOpenAiEndpoint" \
    --azure-openai-embedding-deployment "$AzureOpenAiEmbeddingDeploymentName" \
    --azure-openai-model-name "$AzureOpenAiModelName" \
    --azure-openai-model-dimensions "$AzureOpenAiModelDimensions" \
    --azure-ai-services-endpoint "$AzureAIServicesEndpoint" \
    --azure-search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --use-ocr \
    --verbose
elif [ "$use_document_layout" = "True" ]; then
  echo "use_document_layout is enabled."
  python skillset.py \
    --azure-openai-endpoint "$AzureOpenAiEndpoint" \
    --azure-openai-embedding-deployment "$AzureOpenAiEmbeddingDeploymentName" \
    --azure-openai-model-name "$AzureOpenAiModelName" \
    --azure-openai-model-dimensions "$AzureOpenAiModelDimensions" \
    --azure-ai-services-endpoint "$AzureAIServicesEndpoint" \
    --azure-search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --use-document-layout \
    --verbose
else
  python skillset.py \
    --azure-openai-endpoint "$AzureOpenAiEndpoint" \
    --azure-openai-embedding-deployment "$AzureOpenAiEmbeddingDeploymentName" \
    --azure-openai-model-name "$AzureOpenAiModelName" \
    --azure-openai-model-dimensions "$AzureOpenAiModelDimensions" \
    --azure-ai-services-endpoint "$AzureAIServicesEndpoint" \
    --azure-search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --verbose
fi

# Step 6: Deploy indexer
echo "Deploying indexer..."
# check if use_ocr is enabled or use_document_layout is enabled and pass the appropriate flag
if [ "$use_ocr" = "True" ]; then
  echo "use_ocr is enabled."
  python indexer.py \
    --search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --use-ocr \
    --interval "$IndexerInterval" \
    --verbose
elif [ "$use_document_layout" = "True" ]; then
  echo "use_document_layout is enabled."
  python indexer.py \
    --search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --use-document-layout \
    --interval "$IndexerInterval" \
    --verbose
else
  python indexer.py \
    --search-endpoint "$SearchEndpoint" \
    --index-name "$IndexName" \
    --interval "$IndexerInterval" \
    --verbose
fi

# Step 7: Test index
echo "Testing index..."
python search_test.py \
  --search-endpoint "$SearchEndpoint" \
  --index-name "$IndexName" \
  --query "$TestQuery" \
  --verbose

# display success message only if all the steps are successful
if [ $? -eq 0 ]; then
  echo "Test completed successfully."
else
  echo "An error occurred during deployment."
  exit 1
fi
echo "Deployment completed successfully."

# # Clean up the Conda environment
# conda deactivate

# conda env remove --name "$CONDA_ENV_NAME"
