import requests
from rdflib import Graph, URIRef, BNode, Literal
from tqdm import tqdm
import pickle
from time import sleep
from wdcuration import lookup_multiple_ids, query_wikidata
from pathlib import Path
import logging
from rdflib.namespace import Namespace
from pathlib import Path

HERE = Path(__file__).parent.resolve()
DATA = HERE.parent.joinpath("data").resolve()
RESULTS = HERE.parent.joinpath("results").resolve()

# Configure logging
logging.basicConfig(filename="unmatched_chembl_ids.log", level=logging.INFO)


def read_tsv(input_file):
    drug_ids, target_ids = [], []
    with input_file.open("r") as file:
        next(file)  # Skip header
        for line in file:
            drug, target = line.strip().split("\t")
            drug_ids.append(drug)
            target_ids.append(target)
    return drug_ids, target_ids


def lookup_with_cache(ids, wikidata_property, cache_file):
    try:
        # Attempt to load the cached lookup results
        with open(cache_file, "rb") as file:
            cached_qids = pickle.load(file)
    except FileNotFoundError:
        # If cache file does not exist, perform the lookup and save the results
        cached_qids = lookup_multiple_ids(ids, wikidata_property)
        with open(cache_file, "wb") as file:
            pickle.dump(cached_qids, file)
    return cached_qids


def get_encoded_proteins(target_qids, chunk_size=200):
    encoded_proteins = {}

    # Split target QIDs into chunks
    chunks = [
        list(target_qids.values())[i : i + chunk_size]
        for i in range(0, len(target_qids), chunk_size)
    ]

    multiple_protein_genes = []

    for chunk in tqdm(chunks):
        formatted_qids = " wd:".join(chunk)
        query = f"""
            SELECT ?gene ?protein
            WHERE {{
                VALUES ?gene {{ wd:{formatted_qids} }} .
                ?gene wdt:P688 ?protein .
            }}
            """
        results = query_wikidata(query)
        for result in results:
            gene_qid = result["gene"].split("/")[-1]
            protein_qid = result["protein"].split("/")[-1]

            if gene_qid in encoded_proteins:
                # Removing the key-value pair from the dictionary
                encoded_proteins.pop(gene_qid, None)
                multiple_protein_genes.append(gene_qid)
            if gene_qid in multiple_protein_genes:
                continue
            encoded_proteins[gene_qid] = protein_qid
        sleep(0.3)

    return encoded_proteins


def run_drug_mechanism_graphql_query(drug_id):
    url = "https://api.platform.opentargets.org/api/v4/graphql"
    query = """
    query MechanismsOfActionSectionQuery($chemblId: String!) {
      drug(chemblId: $chemblId) {
        id
        mechanismsOfAction {
          rows {
            mechanismOfAction 
            actionType
            targets {
              id
            }
          }
        }
      }
    }

    """
    variables = {"chemblId": drug_id}
    response = requests.post(url, json={"query": query, "variables": variables})
    return response.json()


# ... Other functions remain unchanged ...


def create_rdf(drug_ids, target_ids):
    g = Graph()

    # Define Namespaces
    wd = Namespace("http://www.wikidata.org/entity/")
    p = Namespace("http://www.wikidata.org/prop/")
    ps = Namespace("http://www.wikidata.org/prop/statement/")
    rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")

    # Bind namespaces
    g.bind("wd", wd)
    g.bind("p", p)
    g.bind("ps", ps)
    g.bind("rdfs", rdfs)

    drug_ids_for_lookup = list(set(drug_ids))
    target_ids_for_lookup = list(set(target_ids))

    # Lookup Wikidata QIDs for the drug and target IDs using cache
    drug_qids = lookup_with_cache(
        drug_ids_for_lookup, "P592", RESULTS / "drug_qids_cache.pkl"
    )
    target_qids = lookup_with_cache(
        target_ids_for_lookup, "P594", RESULTS / "target_qids_cache.pkl"
    )

    # Lookup encoded proteins for all target QIDs in chunks
    encoded_proteins = get_encoded_proteins(target_qids)

    # Keep track of triples to avoid duplicates
    seen_triples = set()

    # Loop through distinct drug_ids
    for drug_id in tqdm(set(drug_ids)):
        try:
            drug_qid = drug_qids[drug_id]

            response = run_drug_mechanism_graphql_query(drug_id)
            if response["data"]["drug"]["mechanismsOfAction"] is None:
                continue
            for row in response["data"]["drug"]["mechanismsOfAction"]["rows"]:
                for target in row["targets"]:
                    target_id = target["id"]
                    target_qid = target_qids[target_id]
                    encoded_protein_qid = encoded_proteins.get(target_qid)

                    action_type = row["actionType"]
                    statement = BNode()
                    triples = [
                        (wd[drug_qid], p["P129"], statement),
                        (statement, ps["P129"], wd[encoded_protein_qid]),
                        (statement, rdfs["comment"], Literal(action_type)),
                    ]
                    # Only add unique triples
                    for triple in triples:
                        if triple not in seen_triples:
                            g.add(triple)
                            seen_triples.add(triple)
        except KeyError as e:
            logging.info(e)

    return g


def main():
    input_file = RESULTS / "linkedTargets.tsv"
    output_file = RESULTS / "linkedTargets.ttl"

    drug_ids, target_ids = read_tsv(input_file)
    rdf_graph = create_rdf(drug_ids, target_ids)
    rdf_graph.serialize(destination=output_file, format="turtle")


if __name__ == "__main__":
    main()
