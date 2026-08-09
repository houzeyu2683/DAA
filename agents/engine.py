import os

import dotenv
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

def get_model() -> ChatOpenAI:
    """"""
    
    model = ChatOpenAI(
        model=os.environ["MODEL_NAME"],
        base_url=os.environ["MODEL_URL"],
        api_key=os.environ["MODEL_KEY"],
        temperature=0,
    )
    return model
