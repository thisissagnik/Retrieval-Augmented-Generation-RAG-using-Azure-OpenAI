import os
import logging
import argparse

from azure.search.documents.indexes.models import (
    SplitSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    AzureOpenAIEmbeddingSkill,
    OcrSkill,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    IndexProjectionMode,
    SearchIndexerSkillset,
    AIServicesAccountKey,
    AIServicesAccountIdentity,
    DocumentIntelligenceLayoutSkill,
)
from azure.search.documents.indexes import SearchIndexerClient
from azure.core.credentials import AzureKeyCredential


class AISearchSkillset:
    def __init__(self, args):
        # self.args = args
        self.azure_openai_endpoint = args.azure_openai_endpoint
        self.azure_openai_embedding_deployment = args.azure_openai_embedding_deployment
        self.azure_openai_model_name = args.azure_openai_model_name
        self.azure_openai_model_dimensions = args.azure_openai_model_dimensions
        self.azure_ai_services_endpoint = args.azure_ai_services_endpoint
        self.azure_search_endpoint = args.azure_search_endpoint
        self.index_name = args.index_name
        self.skillset_name = f"{self.index_name}-skillset"
        self.use_ocr = args.use_ocr
        self.use_document_layout = args.use_document_layout

    def create_ocr_skillset(self):
        ocr_skill = OcrSkill(
            description="OCR skill to scan PDFs and other images with text",
            context="/document/normalized_images/*",
            line_ending="Space",
            default_language_code="en",
            should_detect_orientation=True,
            inputs=[
                InputFieldMappingEntry(
                    name="image", source="/document/normalized_images/*"
                )
            ],
            outputs=[
                OutputFieldMappingEntry(name="text", target_name="text"),
                OutputFieldMappingEntry(name="layoutText", target_name="layoutText"),
            ],
        )

        split_skill = SplitSkill(
            description="Split skill to chunk documents",
            text_split_mode="pages",
            context="/document/normalized_images/*",
            maximum_page_length=2000,
            page_overlap_length=500,
            inputs=[
                InputFieldMappingEntry(
                    name="text", source="/document/normalized_images/*/text"
                ),
            ],
            outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")],
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            description="Skill to generate embeddings via Azure OpenAI",
            context="/document/normalized_images/*/pages/*",
            resource_url=self.azure_openai_endpoint,
            deployment_name=self.azure_openai_embedding_deployment,
            model_name=self.azure_openai_model_name,
            dimensions=int(self.azure_openai_model_dimensions),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            inputs=[
                InputFieldMappingEntry(
                    name="text", source="/document/normalized_images/*/pages/*"
                ),
            ],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="vector")],
        )

        index_projections = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.index_name,
                    parent_key_field_name="parent_id",
                    source_context="/document/normalized_images/*/pages/*",
                    mappings=[
                        InputFieldMappingEntry(
                            name="chunk", source="/document/normalized_images/*/pages/*"
                        ),
                        InputFieldMappingEntry(
                            name="vector",
                            source="/document/normalized_images/*/pages/*/vector",
                        ),
                        InputFieldMappingEntry(
                            name="title", source="/document/metadata_storage_name"
                        ),
                        InputFieldMappingEntry(
                            name="page_number",
                            source="/document/normalized_images/*/pageNumber",
                        ),
                    ],
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
            ),
        )

        skills = [ocr_skill, split_skill, embedding_skill]

        return SearchIndexerSkillset(
            name=self.skillset_name,
            description="Skillset to chunk documents and generating embeddings",
            skills=skills,
            index_projection=index_projections,
            cognitive_services_account=(
                AIServicesAccountKey(
                    key=os.getenv("AZURE_AI_SERVICE_KEY"),
                    subdomain_url=self.azure_ai_services_endpoint,
                )
                if os.getenv("AZURE_AI_SERVICE_KEY")
                else AIServicesAccountIdentity(
                    identity=None, subdomain_url=self.azure_ai_services_endpoint
                )
            ),
        )

    def create_layout_skillset(self):
        layout_skill = DocumentIntelligenceLayoutSkill(
            description="Layout skill to read documents",
            context="/document",
            output_mode="oneToMany",
            markdown_header_depth="h3",
            inputs=[
                InputFieldMappingEntry(name="file_data", source="/document/file_data")
            ],
            outputs=[
                OutputFieldMappingEntry(
                    name="markdown_document", target_name="markdownDocument"
                )
            ],
        )

        split_skill = SplitSkill(
            description="Split skill to chunk documents",
            text_split_mode="pages",
            context="/document/markdownDocument/*",
            maximum_page_length=2000,
            page_overlap_length=500,
            inputs=[
                InputFieldMappingEntry(
                    name="text", source="/document/markdownDocument/*/content"
                ),
            ],
            outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")],
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            description="Skill to generate embeddings via Azure OpenAI",
            context="/document/markdownDocument/*/pages/*",
            resource_url=self.azure_openai_endpoint,
            deployment_name=self.azure_openai_embedding_deployment,
            model_name=self.azure_openai_model_name,
            dimensions=int(self.azure_openai_model_dimensions),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            inputs=[
                InputFieldMappingEntry(
                    name="text", source="/document/markdownDocument/*/pages/*"
                ),
            ],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="vector")],
        )

        index_projections = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.index_name,
                    parent_key_field_name="parent_id",
                    source_context="/document/markdownDocument/*/pages/*",
                    mappings=[
                        InputFieldMappingEntry(
                            name="chunk", source="/document/markdownDocument/*/pages/*"
                        ),
                        InputFieldMappingEntry(
                            name="vector",
                            source="/document/markdownDocument/*/pages/*/vector",
                        ),
                        InputFieldMappingEntry(
                            name="title", source="/document/metadata_storage_name"
                        ),
                        InputFieldMappingEntry(
                            name="header_1",
                            source="/document/markdownDocument/*/sections/h1",
                        ),
                        InputFieldMappingEntry(
                            name="header_2",
                            source="/document/markdownDocument/*/sections/h2",
                        ),
                        InputFieldMappingEntry(
                            name="header_3",
                            source="/document/markdownDocument/*/sections/h3",
                        ),
                    ],
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
            ),
        )

        skills = [layout_skill, split_skill, embedding_skill]

        return SearchIndexerSkillset(
            name=self.skillset_name,
            description="Skillset to chunk documents and generating embeddings",
            skills=skills,
            index_projection=index_projections,
            cognitive_services_account=(
                AIServicesAccountKey(
                    key=os.getenv("AZURE_AI_SERVICE_KEY"),
                    subdomain_url=self.azure_ai_services_endpoint,
                )
                if os.getenv("AZURE_AI_SERVICE_KEY")
                else AIServicesAccountIdentity(
                    identity=None, subdomain_url=self.azure_ai_services_endpoint
                )
            ),
        )

    def create_ai_skillset(self):
        split_skill = SplitSkill(
            description="Split skill to chunk documents",
            text_split_mode="pages",
            context="/document",
            maximum_page_length=2000,
            page_overlap_length=500,
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/content"),
            ],
            outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")],
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            description="Skill to generate embeddings via Azure OpenAI",
            context="/document/pages/*",
            resource_url=self.azure_openai_endpoint,
            deployment_name=self.azure_openai_embedding_deployment,
            model_name=self.azure_openai_model_name,
            dimensions=int(self.azure_openai_model_dimensions),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/pages/*"),
            ],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="vector")],
        )

        index_projections = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.index_name,
                    parent_key_field_name="parent_id",
                    source_context="/document/pages/*",
                    mappings=[
                        InputFieldMappingEntry(
                            name="chunk", source="/document/pages/*"
                        ),
                        InputFieldMappingEntry(
                            name="vector", source="/document/pages/*/vector"
                        ),
                        InputFieldMappingEntry(
                            name="title", source="/document/metadata_storage_name"
                        ),
                    ],
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
            ),
        )

        skills = [split_skill, embedding_skill]

        return SearchIndexerSkillset(
            name=self.skillset_name,
            description="Skillset to chunk documents and generating embeddings",
            skills=skills,
            index_projection=index_projections,
        )

    def create_skillset(self):
        use_ocr = self.use_ocr
        use_document_layout = self.use_document_layout
        skillset = (
            self.create_ocr_skillset()
            if use_ocr
            else (
                self.create_layout_skillset()
                if use_document_layout
                else self.create_ai_skillset()
            )
        )

        client = SearchIndexerClient(
            self.azure_search_endpoint,
            AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY")),
        )
        client.create_or_update_skillset(skillset)
        logging.info("Skillset %s created", skillset.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--azure-openai-endpoint", type=str, required=True)
    parser.add_argument("--azure-openai-embedding-deployment", type=str, required=True)
    parser.add_argument("--azure-openai-model-name", type=str, required=True)
    parser.add_argument("--azure-openai-model-dimensions", type=int, required=False, default=1536)
    parser.add_argument("--azure-ai-services-endpoint", type=str, required=True)
    parser.add_argument("--azure-search-endpoint", type=str, required=True)
    parser.add_argument("--index-name", type=str, required=True)
    parser.add_argument("--use-ocr", action="store_true", default=False)
    parser.add_argument("--use-document-layout", action="store_true", default=False)
    parser.add_argument("--verbose", action="store_true", required=False, default=False)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Azure Search Endpoint: %s", args.azure_search_endpoint)
    logging.debug("Index Name: %s", args.index_name)
    logging.debug("Use OCR: %s", args.use_ocr)
    logging.debug("Use Document Layout: %s", args.use_document_layout)
    logging.debug("Azure OpenAI Endpoint: %s", args.azure_openai_endpoint)
    logging.debug(
        "Azure OpenAI Embedding Deployment: %s", args.azure_openai_embedding_deployment
    )
    logging.debug("Azure OpenAI Model Name: %s", args.azure_openai_model_name)
    logging.debug(
        "Azure OpenAI Model Dimensions: %s", args.azure_openai_model_dimensions
    )
    logging.debug("Azure AI Services Endpoint: %s", args.azure_ai_services_endpoint)

    skillset = AISearchSkillset(args)
    skillset.create_skillset()


if __name__ == "__main__":
    main()
