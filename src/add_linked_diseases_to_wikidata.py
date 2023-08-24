import pandas as pd
import json
import os
import time
import logging
from wikibaseintegrator import wbi_login, WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists
from login import USER, PASS
from wikibaseintegrator.models import References, Reference
from wdcuration import query_wikidata
from pathlib import Path

HERE = Path(__file__).parent.resolve()
DATA = HERE.parent.joinpath("data").resolve()
RESULTS = HERE.parent.joinpath("results").resolve()
logging.basicConfig(level=logging.INFO)

CACHE_FILE = HERE / "dicts" / "id_mappings.json"
CACHE_DURATION = 259200  # 3 days in seconds


def create_id_mapping(prop, prefix=None):
    """Function to create a mapping of IDs to QIDs"""
    query = f"""
    SELECT ?id ?item WHERE {{
        ?item wdt:{prop} ?id.
    }}
    """
    results = query_wikidata(query)
    mapping = {}
    for entry in results:
        id_value = entry["id"]
        if ":" in id_value:
            id_value = id_value.split(":")[-1]
        if prefix:
            id_value = prefix + id_value
        mapping[id_value] = entry["item"].replace("http://www.wikidata.org/entity/", "")
    return mapping


def load_or_update_mappings():
    # Check if the cache exists
    if os.path.exists(CACHE_FILE):
        cache_mod_time = os.path.getmtime(CACHE_FILE)
        current_time = time.time()
        if current_time - cache_mod_time < CACHE_DURATION:
            with open(CACHE_FILE, "r") as f:
                logging.info("Loading mappings from cache.")
                return json.load(f)

    logging.info("Updating mappings from Wikidata.")
    efo_to_qid = create_id_mapping("P11956", prefix="EFO_")
    orphanet_to_qid = create_id_mapping("P1550", prefix="Orphanet_")
    mondo_to_qid = create_id_mapping("P5270", prefix="MONDO_")
    ensg_to_qid = create_id_mapping("P594")
    mappings = {
        "efo_to_qid": efo_to_qid,
        "orphanet_to_qid": orphanet_to_qid,
        "mondo_to_qid": mondo_to_qid,
        "ensg_to_qid": ensg_to_qid,
    }

    with open(CACHE_FILE, "w") as f:
        json.dump(mappings, f)

    return mappings


mappings = load_or_update_mappings()
efo_to_qid = mappings["efo_to_qid"]
orphanet_to_qid = mappings["orphanet_to_qid"]
mondo_to_qid = mappings["mondo_to_qid"]
ensg_to_qid = mappings["ensg_to_qid"]
all_diseases_to_qid = {**efo_to_qid, **orphanet_to_qid, **mondo_to_qid}

# Load the data from TSV
df = pd.read_csv(RESULTS / "linkedDiseases.tsv", sep="\t")

# Configure and login to Wikibase
wbi_config[
    "USER_AGENT"
] = "TiagoLubiana (https://www.wikidata.org/wiki/User:TiagoLubiana)"
login_instance = wbi_login.Clientlogin(user=USER, password=PASS)
wbi = WikibaseIntegrator(login=login_instance)


# Iterate over the DataFrame grouped by disease to batch add claims for each disease
for diseaseId, group in df.groupby("diseaseId"):
    if diseaseId != "MONDO_0000463":
        continue
    disease_wd = all_diseases_to_qid.get(diseaseId)

    if not disease_wd:
        logging.warning(f"{diseaseId} not found on Wikidata!")
        continue

    item = wbi.item.get(entity_id=disease_wd)

    for _, row in group.iterrows():
        target_wd = ensg_to_qid.get(row["targetId"])

        if not target_wd:
            logging.warning(f"{row['targetId']} not found on Wikidata!")
            continue

        references = References()
        # Add your references. The following is a placeholder for illustration.
        open_targets_reference = Reference()
        open_targets_reference.add(datatypes.Item(prop_nr="P248", value="Q113138000"))
        open_targets_reference.add(
            datatypes.Time("+2023-08-24T00:00:00Z", prop_nr="P813")
        )
        open_targets_reference.add(
            datatypes.URL(
                f"https://platform.opentargets.org/evidence/{row['targetId']}/{diseaseId}",
                prop_nr="P854",
            )
        )
        open_targets_reference.add(datatypes.Item(prop_nr="P887", value="Q121819027"))

        references.add(open_targets_reference)

        # Create the claim for the disease item
        claim = datatypes.Item(
            prop_nr="P2293",
            value=target_wd,
            references=references,
        )
        item.claims.add(claim, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)

        # Create the claim in reverse for the target item
        target_item = wbi.item.get(entity_id=target_wd)
        inverse_claim = datatypes.Item(
            prop_nr="P2293",
            value=disease_wd,
            references=references,
        )
        target_item.claims.add(
            inverse_claim, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND
        )
        target_item.write(summary="Update genetic associations from Open Targets.")

    # Write the item after adding all claims for this disease
    item.write(summary="Update genetic associations from Open Targets.")
