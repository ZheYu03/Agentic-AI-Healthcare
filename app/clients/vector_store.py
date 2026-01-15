from typing import Optional

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.core.config import Settings


def build_vector_store(settings: Settings) -> Optional[PineconeVectorStore]:
    """
    Configure a Pinecone vector store using Gemini embeddings.

    Returns None if VECTOR_STORE_MODE is not set to a supported value.
    """
    if settings.vector_store_mode != "cloud":
        return None

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large", dimensions=1536, api_key=settings.openai_api_key
    )
    return PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=embeddings,
        pinecone_api_key=settings.pinecone_api_key,
    )
