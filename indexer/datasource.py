import argparse
import logging
import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.identity import AzureCliCredential
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential

from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
)

from azure.search.documents.indexes.models import (
    HighWaterMarkChangeDetectionPolicy,
    SoftDeleteColumnDeletionDetectionPolicy,
)

logging.basicConfig(level=logging.DEBUG)


_logger = logging.getLogger(__name__)


class AISearchDataSource:

    def __init__(self, args):
        self.args = args

    def ensure_container_exists(
        self,
        storage_account_url: str,
        container_name: str,
        credential=None,
    ):
        """Ensure container exists

        Args:
            storage_account_url (_type_): storage account url
            container_name (_type_): container name
            credential (_type_): credential
        Raises:
            Exception: exception in case of failure

        Returns:
            _type_: response
        """
        try:

            _blob_service_client = BlobServiceClient(
                account_url=storage_account_url,
                credential=credential,
            )
            _container_client = _blob_service_client.get_container_client(
                container=container_name
            )
            if not _container_client.exists():
                _container_client.create_container()
        except Exception as e:
            _logger.error(str(e))
            raise e
        finally:
            pass

    def create_data_source(self):

        _args = self.args

        # _credential = ClientSecretCredential(os.getenv("AZURE_TENANT_ID"), os.getenv("AZURE_CLIENT_ID"), os.getenv("AZURE_CLIENT_SECRET"))
        # _credential = AzureCliCredential()
        # _credential = DefaultAzureCredential()

        _search_endpoint = _args.search_endpoint
        _index_name = _args.index_name
        _subscription_id = _args.subscription_id
        _resource_group_name = _args.resource_group_name
        _storage_account_name = _args.storage_account_name
        _storage_account_url = _args.storage_account_url
        _container_name = _args.container_name

        self.ensure_container_exists(
            storage_account_url=_storage_account_url,
            container_name=_container_name,
            credential=os.getenv("AZURE_STORAGE_KEY"),
        )

        _search_blob_connection_string = f"ResourceId=/subscriptions/{_subscription_id}/resourceGroups/{_resource_group_name}/providers/Microsoft.Storage/storageAccounts/{_storage_account_name}"
        
        # _indexer_client = SearchIndexerClient(_search_endpoint, _credential)
        _container = SearchIndexerDataContainer(name=_container_name)
        _data_source_connection = SearchIndexerDataSourceConnection(
            name=f"{_index_name}-blob",
            type="azureblob",
            connection_string=_search_blob_connection_string,
            container=_container,
            data_change_detection_policy=HighWaterMarkChangeDetectionPolicy(
                high_water_mark_column_name="metadata_storage_last_modified"
            ),
            data_deletion_detection_policy=SoftDeleteColumnDeletionDetectionPolicy(
                soft_delete_column_name="Status",
                soft_delete_marker_value="Deleted",
            ),
        )
        # try:
        #     _data_source = _indexer_client.create_or_update_data_source_connection(
        #         _data_source_connection
        #     )
        # except Exception as e:
        #     logging.info(f"Unable to created or update data source using managed identity, trying with search key")
        #     # use Ai Search key as credential
        #     index_client = SearchIndexerClient(_search_endpoint, os.getenv("AZURE_SEARCH_KEY"))
        #     _data_source = index_client.create_or_update_data_source_connection(_data_source_connection)

        index_client = SearchIndexerClient(_search_endpoint, AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY")))
        _data_source = index_client.create_or_update_data_source_connection(_data_source_connection)

        logging.info("Data source %s created or updated", _data_source.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-endpoint",
        type=str,
        help="Azure AI Search endpoint",
    )
    parser.add_argument(
        "--index-name",
        type=str,
        help="Azure AI Search index name",
    )
    parser.add_argument(
        "--subscription-id",
        type=str,
        help="Azure subscription id",
    )
    parser.add_argument(
        "--resource-group-name",
        type=str,
        help="Azure resource group name",
        default="rag-search-poc",
    )
    parser.add_argument(
        "--storage-account-name",
        type=str,
        help="Azure storage account name",
        default="ragsearchpocstorage01",
    )
    parser.add_argument(
        "--storage-account-url",
        type=str,
        help="Azure storage account url",
    )
    parser.add_argument(
        "--container-name",
        type=str,
        help="Azure storage container name",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase output verbosity",
    )
    _args = parser.parse_args()

    if _args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Search endpoint %s", _args.search_endpoint)
    logging.debug("Index name %s", _args.index_name)
    logging.debug("Subscription id %s", _args.subscription_id)
    logging.debug("Resource group name %s", _args.resource_group_name)
    logging.debug("Storage account name %s", _args.storage_account_name)
    logging.debug("Storage account url %s", _args.storage_account_url)
    logging.debug("Container name %s", _args.container_name)

    _ai_search_data_source = AISearchDataSource(_args)
    _ai_search_data_source.create_data_source()


if __name__ == "__main__":
    main()
