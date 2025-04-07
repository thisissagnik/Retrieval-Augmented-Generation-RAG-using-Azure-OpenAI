import os
import logging
import argparse

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes import SearchIndexerClient
from azure.storage.blob import BlobServiceClient



class ManageSearch:
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.args = kwargs.get("args")

    def delete_index(
        self,
    ):

        _args = self.args
        _search_endpoint = _args.search_service_endpoint
        _credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
        _indexer_client = SearchIndexerClient(
            _search_endpoint,
            _credential,
        )

        _index_name = _args.index_name
        _indexer_name = f"{_index_name}-indexer"
        _skillset_name = f"{_index_name}-skillset"
        _data_source_name = f"{_index_name}-blob"

        logging.info(f"Deleting Indexer: {_indexer_name}")
        print(f"Deleting Indexer: {_indexer_name}")
        _indexer_client.delete_indexer(
            indexer=_indexer_name,
        )
        logging.info(f"Deleting Skillset: {_skillset_name}")
        print(f"Deleting Skillset: {_skillset_name}")
        _indexer_client.delete_skillset(
            skillset=_skillset_name,
        )

        logging.info(f"Deleting Data Source: {_data_source_name}")
        print(f"Deleting Data Source: {_data_source_name}")
        _indexer_client.delete_data_source_connection(
            data_source_connection=_data_source_name,
        )

        _index_client = SearchIndexClient(
            endpoint=_search_endpoint,
            credential=_credential,
        )
        logging.info(f"Deleting Index: {_index_name}")
        print(f"Deleting Index: {_index_name}")
        _index_client.delete_index(
            index=_index_name,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Status Metrics")
    parser.add_argument(
        "--storage-account-url",
        type=str,
        help="Storage account url containing the data",
        default=None,
    )
    parser.add_argument(
        "--container-name",
        type=str,
        help="Storage account container name containing the data",
        default=None,
    )
    parser.add_argument(
        "--search-service-endpoint",
        type=str,
        help="Search service url",
        default=None,
    )
    parser.add_argument(
        "--index-name",
        type=str,
        help="Name of the indexer",
        default=None,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose",
        default=False,
    )
    _args = parser.parse_args()


    _manage_search = ManageSearch(
        args=_args
    )
    if (
        _args.search_service_endpoint
        and _args.index_name
        and _args.index_name != "None"
    ):
        _manage_search.delete_index()
