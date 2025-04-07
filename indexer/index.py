import logging
import argparse
import os

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
    SearchIndex,
)

from azure.identity import AzureCliCredential
from azure.core.credentials import AzureKeyCredential


class AISearchIndex:

    def __init__(self, args):
        self.args = args

    def create_index(self):
        _args = self.args
        _credential = AzureCliCredential()
        _search_endpoint = _args.search_endpoint
        _index_name = _args.index_name
        _add_page_numbers = _args.add_page_numbers
        _use_document_layout = _args.use_document_layout

        _azure_openai_endpoint = _args.azure_openai_endpoint
        _azure_openai_embedding_deployment_name = (
            _args.azure_openai_embedding_deployment_name
        )
        _azure_openai_model_name = _args.azure_openai_model_name
        _azure_openai_model_dimensions = _args.azure_openai_model_dimensions

        # Create a search index
        _index_client = SearchIndexClient(
            endpoint=_search_endpoint,
            credential=_credential,
        )
        _fields = [
            SearchField(
                name="parent_id",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="title",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="blob_path",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="source_address",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
                key=True,
                analyzer_name="keyword",
            ),
            SearchField(
                name="chunk",
                type=SearchFieldDataType.String,
                sortable=False,
                filterable=False,
                facetable=False,
            ),
            SearchField(
                name="vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=_azure_openai_model_dimensions,
                vector_search_profile_name=f"{_index_name}HnswProfile",
                hidden=False,
            ),
        ]

        if _add_page_numbers:
            _fields.append(
                SearchField(
                    name="page_number",
                    type=SearchFieldDataType.String,
                    sortable=True,
                    filterable=True,
                    facetable=False,
                )
            )
        if _use_document_layout:
            _fields.extend([
                SearchField(name="header_1", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False),
                SearchField(name="header_2", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False),
                SearchField(name="header_3", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False)
            ])

        # Configure the vector search configuration
        _vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name=f"{_index_name}Hnsw"),
            ],
            profiles=[
                VectorSearchProfile(
                    name=f"{_index_name}HnswProfile",
                    algorithm_configuration_name=f"{_index_name}Hnsw",
                    vectorizer_name=f"{_index_name}OpenAI",
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name=f"{_index_name}OpenAI",
                    kind="azureOpenAI",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=_azure_openai_endpoint,
                        deployment_name=_azure_openai_embedding_deployment_name,
                        model_name=_azure_openai_model_name,
                    ),
                ),
            ],
        )

        _semantic_config = SemanticConfiguration(
            name=f"{_index_name}-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="chunk")]
            ),
        )

        # Create the semantic search with the configuration
        _semantic_search = SemanticSearch(configurations=[_semantic_config])

        # Create the search index
        _index = SearchIndex(
            name=_index_name,
            fields=_fields,
            vector_search=_vector_search,
            semantic_search=_semantic_search,
        )
        try:
            _result = _index_client.create_index(_index)
            logging.info("Index %s created", _result.name)
        except Exception as e:
            logging.info(f"Unable to created or update index using managed identity, trying with search key")
            _index_client = SearchIndexClient(endpoint=_search_endpoint,credential= AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY")))
            _result = _index_client.create_or_update_index(_index)
            logging.info("Index %s created", _result.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-endpoint",
        type=str,
        help="Azure AI Search endpoint",
        required=True,
    )
    parser.add_argument(
        "--index-name",
        type=str,
        help="Azure AI Search index name",
        required=True,
    )
    parser.add_argument(
        "--azure-openai-endpoint",
        type=str,
        help="Azure OpenAI endpoint",
        required=True,
    )
    parser.add_argument(
        "--azure-openai-embedding-deployment-name",
        type=str,
        help="Azure OpenAI embedding deployment",
        required=True,
    )
    parser.add_argument(
        "--azure-openai-model-name",
        type=str,
        help="Azure OpenAI model name",
        required=True,
    )
    parser.add_argument(
        "--azure-openai-model-dimensions",
        type=int,
        help="Azure OpenAI model dimensions",
        required=False,
        default=1536,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase output verbosity",
        required=False,
        default=False,
    )
    parser.add_argument(
        "--add-page-numbers",
        action="store_true",
        help="Add page numbers to the index",
        required=False,
        default=False,
    )
    parser.add_argument(
        "--use-document-layout",
        action="store_true",
        help="Use document layout",
        required=False,
        default=False,
    )
    _args = parser.parse_args()

    if _args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Search endpoint %s", _args.search_endpoint)
    logging.debug("Index name %s", _args.index_name)
    logging.debug("Azure OpenAI endpoint %s", _args.azure_openai_endpoint)
    logging.debug(
        "Azure OpenAI embedding deployment %s",
        _args.azure_openai_embedding_deployment_name,
    )
    logging.debug("Azure OpenAI model name %s", _args.azure_openai_model_name)
    logging.debug(
        "Azure OpenAI model dimensions %s", _args.azure_openai_model_dimensions
    )
    logging.debug("Add page numbers %s", _args.add_page_numbers)
    logging.debug("Use document layout %s", _args.use_document_layout)

    _ai_search_index = AISearchIndex(_args)
    _ai_search_index.create_index()


if __name__ == "__main__":
    main()
