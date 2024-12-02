import os
import spacy
from langchain_community.document_loaders import WikipediaLoader
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

context_prompt = """
You are a data scientist working for a company that is building a graph database. Your task is to extract information from data and convert it into a graph database.
Provide a set of Nodes in the form [ENTITY_ID, TYPE, PROPERTIES] and a set of relationships in the form [ENTITY_ID_1, RELATIONSHIP, ENTITY_ID_2, PROPERTIES].
It is important that the ENTITY_ID_1 and ENTITY_ID_2 exists as nodes with a matching ENTITY_ID. If you can't pair a relationship with a pair of nodes don't add it.
When you find a node or relationship you want to add try to create a generic TYPE for it that describes the entity you can also think of it as a label. 
In your response, only give me the nodes and relationships in json format.

Example:
Data: Alice lawyer and is 25 years old and Bob is her roommate since 2001. Bob works as a journalist. Alice owns a the webpage www.alice.com and Bob owns the webpage www.bob.com.
Nodes: ["alice", "Person", {"age": 25, "occupation": "lawyer", "name":"Alice"}], ["bob", "Person", {"occupation": "journalist", "name": "Bob"}], ["alice.com", "Webpage", {"url": "www.alice.com"}], ["bob.com", "Webpage", {"url": "www.bob.com"}]
Relationships: ["alice", "roommate", "bob", {"start": 2021}], ["alice", "owns", "alice.com", {}], ["bob", "owns", "bob.com", {}]

Here is the Data: 

"""

# Load the environment variables from the .env file
load_dotenv()
page_title = "Machine learning"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

import wikipediaapi

def extract_wikipedia_content(page_title):
    # Define a custom user agent
    user_agent = "WikipediaAPI/0.5 (Academic Project; taidersami1@gmail.com)"  # Replace with your email

    # Initialize Wikipedia API with language and user agent
    wiki_wiki = wikipediaapi.Wikipedia(
        language="en",
        extract_format=wikipediaapi.ExtractFormat.WIKI,
        user_agent=user_agent,
    )

    # Fetch the page
    page = wiki_wiki.page(page_title)

    # Check if the page exists
    if page.exists():
        return page.text
    else:
        print("Page does not exist!")
        return None

def process_wikipedia_content(page_title):
    content = extract_wikipedia_content(page_title)
    if content:
        # Process the text with spaCy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(content)

        # Tokenize sentences
        sentences = [sent.text for sent in doc.sents]
        print("Sentences:", sentences)

        # Remove stop words and non-alphanumeric tokens
        filtered_tokens = [token.text for token in doc if not token.is_stop]
        print("Filtered Tokens:", filtered_tokens)

        # Extract entities
        for ent in doc.ents:
            print(f"Entity: {ent.text}, Label: {ent.label_}")

def chat_with_gpt(prompt):

    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-3.5-turbo",
    )

    return chat_completion.choices[0].message["content"]

def txt_file_from_str(string, filename="output.txt"):
    with open(filename, "w", encoding="UTF-8") as text_file:
        text_file.write(string)

def extract_entities_and_relationships(content):
    prompt = context_prompt + content
    response = chat_with_gpt(prompt)
    return response

# split the content into parts of length n characters
def split_content(length, content):
    parts = []
    while len(content) > length:
        last_period = content[:length].rfind(".")
        parts.append(content[:last_period])
        content = content[last_period:]
    parts.append(content)
    return parts

content = extract_wikipedia_content(page_title)
txt_file_from_str(context_prompt + split_content(1000, content[:2000])[0])