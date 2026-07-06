from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from os import getenv

_ = load_dotenv()

def get_model(response_format=None) -> ChatOpenAI:
    if response_format:
        model = ChatOpenAI(
            base_url=getenv("MODEL_URL"),
            api_key=getenv("API_KEY"),
            model=getenv("MODEL_NAME"),
            temperature=0,
            response_format=response_format
        )
        return model

    model = ChatOpenAI(
        base_url=getenv("MODEL_URL"),
        api_key=getenv("API_KEY"),
        model=getenv("MODEL_NAME"),
        temperature=0
    )
    return model

