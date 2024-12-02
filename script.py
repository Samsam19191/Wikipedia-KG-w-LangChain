import os
from neo4j import GraphDatabase
import spacy
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import wikipediaapi


context_prompt = """
You are a data scientist working for a company that is building a graph database. Your task is to extract information from data and convert it into a graph database.
Provide a set of Nodes in the form [ENTITY_ID, TYPE, PROPERTIES] and a set of relationships in the form [ENTITY_ID_1, RELATIONSHIP, ENTITY_ID_2, PROPERTIES].
It is important that the ENTITY_ID_1 and ENTITY_ID_2 exists as nodes with a matching ENTITY_ID. If you can't pair a relationship with a pair of nodes don't add it.
When you find a node or relationship you want to add try to create a generic TYPE for it that describes the entity you can also think of it as a label. 
In your response, only give me the nodes and relationships in json format.
The propery names should be a single word.

Example:
Data: Alice lawyer and is 25 years old and Bob is her roommate since 2001. Bob works as a journalist. Alice owns a the webpage www.alice.com and Bob owns the webpage www.bob.com.
Nodes: ["alice", "Person", {"age": 25, "occupation": "lawyer", "name":"Alice"}], ["bob", "Person", {"occupation": "journalist", "name": "Bob"}], ["alice.com", "Webpage", {"url": "www.alice.com"}], ["bob.com", "Webpage", {"url": "www.bob.com"}]
Relationships: ["alice", "roommate", "bob", {"start": 2021}], ["alice", "owns", "alice.com", {}], ["bob", "owns", "bob.com", {}]

Here is the Data: 

"""

load_dotenv()
page_title = "Machine learning"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")


def run_cypher_query(query, driver):
    with driver.session() as session:
        result = session.run(query)
        return result


def extract_wikipedia_content(page_title):
    user_agent = "WikipediaAPI/0.5 (Academic Project; taidersami1@gmail.com)"  # Replace with your email

    wiki_wiki = wikipediaapi.Wikipedia(
        language="en",
        extract_format=wikipediaapi.ExtractFormat.WIKI,
        user_agent=user_agent,
    )

    page = wiki_wiki.page(page_title)

    if page.exists():
        return page.text
    else:
        print("Page does not exist!")
        return None


# Process the text with spaCy
def process_wikipedia_content(content):
    if content:
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(content)

        filtered_content = ""
        for sent in doc.sents:
            filtered_tokens = [token.text for token in sent if not token.is_stop]
            filtered_sentence = " ".join(filtered_tokens)
            filtered_content += filtered_sentence + "\n"
        return filtered_content


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


def aggregarte_json_responses(json_responses):
    data = json.loads(json_responses[0])
    nodes = data["nodes"]
    relationships = data["relationships"]
    for i in range(1, len(json_responses)):
        data = json.loads(json_responses[i])
        nodes.extend(data["nodes"])
        relationships.extend(data["relationships"])
    return json.dumps({"nodes": nodes, "relationships": relationships})


def Json_to_cypher(Json_response):
    data = json.loads(Json_response)
    nodes = data["nodes"]
    relationships = data["relationships"]

    cypher_query = ""

    # For nodes
    for node in nodes:
        node_ID = node[0]
        node_type = node[1]
        properties = node[2]

        property_str = ", ".join(
            [f'{key}: "{value}"' for key, value in properties.items()]
        )

        cypher_query += f"CREATE ({node_ID}:{node_type} {{{property_str}}})\n"

    # For relationships
    for relationship in relationships:
        properties = relationship[3]
        property_str = ", ".join(
            [f'{key}: "{value}"' for key, value in properties.items()]
        )
        cypher_query += f"CREATE ({relationship[0]})-[:{relationship[1]} {{{property_str}}}]->({relationship[2]})\n"

    return cypher_query


def generate_graph(page_title):
    content = extract_wikipedia_content(page_title)
    Json_response = extract_entities_and_relationships(content)
    cypher_query = Json_to_cypher(Json_response)
    driver = GraphDatabase.driver(uri, auth=(username, password))
    run_cypher_query(cypher_query, driver)
    driver.close()


def generate_graph_with_processed_content(page_title):
    content = extract_wikipedia_content(page_title)
    processed_content = process_wikipedia_content(content)
    Json_response = extract_entities_and_relationships(processed_content)
    cypher_query = Json_to_cypher(Json_response)
    driver = GraphDatabase.driver(uri, auth=(username, password))
    run_cypher_query(cypher_query, driver)
    driver.close()