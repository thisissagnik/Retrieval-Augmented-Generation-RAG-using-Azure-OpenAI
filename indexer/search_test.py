import logging
import argparse
import os
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from azure.identity import AzureCliCredential
from azure.core.credentials import AzureKeyCredential


class AISearchTest:
    def __init__(self, args):
        self.args = args

    def search(self):
        _args = self.args
        # _credential = AzureCliCredential()
        _credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))

        _search_endpoint = _args.search_endpoint
        _index_name = _args.index_name
        _add_page_numbers = _args.add_page_numbers
        _query = _args.query

        # Pure Vector Search
        _search_client = SearchClient(
            _search_endpoint,
            _index_name,
            credential=_credential,
        )
        _vector_query = VectorizableTextQuery(
            text=_query,
            k_nearest_neighbors=1,
            fields="vector",
            exhaustive=True,
        )
        # Use the below query to pass in the raw vector query instead of the query vectorization
        # vector_query = RawVectorQuery(vector=generate_embeddings(query), k_nearest_neighbors=3, fields="vector")

        _results = _search_client.search(
            search_text=None, vector_queries=[_vector_query], top=1
        )

        for _result in _results:
            print(f"parent_id: {_result['parent_id']}")
            print(f"chunk_id: {_result['chunk_id']}")
            if _add_page_numbers:
                print(f"page_number: {_result['page_number']}")
            print(f"Score: {_result['@search.score']}")
            _chunk = _result["chunk"].replace("\n", " ")
            print(f"Content: {_chunk}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-endpoint",
        required=True,
        help="Search endpoint",
    )
    parser.add_argument(
        "--index-name",
        required=True,
        help="Index name",
    )
    parser.add_argument(
        "--add-page-numbers",
        action="store_true",
        help="Add page numbers",
        required=False,
        default=False,
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Query",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose",
        required=False,
        default=False,
    )
    _args = parser.parse_args()

    if _args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Search endpoint: %s", _args.search_endpoint)
    logging.debug("Index name: %s", _args.index_name)
    logging.debug("Add page numbers: %s", _args.add_page_numbers)
    logging.debug("Query: %s", _args.query)

    _search_test = AISearchTest(_args)
    _search_test.search()


if __name__ == "__main__":
    main()
