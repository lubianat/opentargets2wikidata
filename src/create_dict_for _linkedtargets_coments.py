from rdflib import Graph, Namespace
from pathlib import Path
from rdflib import Graph, Namespace
from pathlib import Path
import json
from typing import List

# wdcuration imports
from wdcuration import check_and_save_dict, NewItemConfig

# Locate the linkedTargets.ttl file
current_path = Path(__file__).parent
ttl_file_path = current_path.parent / "linkedTargets.ttl"

# Create an RDF graph
g = Graph()

# Read and parse the RDF data
with ttl_file_path.open("r") as file:
    g.parse(file, format="turtle")

# Namespace for rdfs
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

# Query the graph to get all rdfs:comment values
qres = g.query(
    """
    SELECT ?comment
    WHERE {
        ?s rdfs:comment ?comment .
    }
"""
)

# Store the results in a Python list
comments = [row[0].value for row in qres]


# Deduplicate the comments using a set
unique_comments = set(comments)

# Load the master dictionary (you can modify this according to where you keep your dictionary)
master_dict_path = current_path / "dicts"
dict_name = "action_types"  # replace with your target dict name

master_dict = {}
# Load the existing dictionary if it exists
if (master_dict_path / f"{dict_name}.json").exists():
    master_dict[dict_name] = json.loads(
        (master_dict_path / f"{dict_name}.json").read_text()
    )
else:
    master_dict = {dict_name: {}}

# Setup for new item creation (customize as necessary)
new_item_config = NewItemConfig(
    labels={"en": "default_label"}, descriptions={"en": "default_description"}
)

blacklisted_comments = "ANTISENSE INHIBITOR", "OTHER"
# Check and save the term in the dictionary
for comment in unique_comments:
    if comment in blacklisted_comments:
        continue
    check_and_save_dict(
        master_dict, dict_name, comment, master_dict_path, format_function=str
    )
