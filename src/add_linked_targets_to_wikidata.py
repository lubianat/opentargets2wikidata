import json
from pathlib import Path
from rdflib import Graph, Namespace
from wikibaseintegrator import wbi_login, WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists

from login import USER, PASS
from wikibaseintegrator.models import Qualifiers, References, Reference

# Load the action types dictionary
action_types_path = Path("src/dicts/action_types.json")
with action_types_path.open() as f:
    action_types = json.load(f)

# Configure and login to Wikibase
wbi_config[
    "USER_AGENT"
] = "TiagoLubiana (https://www.wikidata.org/wiki/User:TiagoLubiana)"
login_instance = wbi_login.Clientlogin(user=USER, password=PASS)

wbi = WikibaseIntegrator(login=login_instance)


# Load and parse the RDF file
g = Graph()
g.parse("linkedTargets.ttl", format="turtle")

# Define the namespaces
wd = Namespace("http://www.wikidata.org/entity/")
p = Namespace("http://www.wikidata.org/prop/")
ps = Namespace("http://www.wikidata.org/prop/statement/")
rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")

flag = 0
# Process the triples and create claims
for subj, pred, obj in g.triples((None, p.P129, None)):
    subj_wd = str(subj).replace(wd, "")
    item = wbi.item.get(entity_id=subj_wd)

    obj_comment = None
    obj_wd = None

    # For each statement object, extract the value and the qualifier
    for o_pred, o_obj in g.predicate_objects(subject=obj):
        if o_pred == rdfs.comment:
            obj_comment = str(o_obj).upper()
        elif o_pred == ps.P129:
            obj_wd = str(o_obj).replace(wd, "")

    # Check if we successfully parsed the value and the qualifier
    if obj_comment and obj_wd:
        action_wd = action_types.get(obj_comment, None)

        if action_wd:
            qualifiers = Qualifiers()
            qualifiers.add(
                datatypes.Item(prop_nr="P2868", value=action_wd)
            )  # Adding the qualifier from the dictionary

            all_references = References()

            open_targets_reference = Reference()
            open_targets_reference.add(
                datatypes.Item(prop_nr="P248", value="Q113138000")
            )
            open_targets_reference.add(
                datatypes.Time(
                    "+2023-08-14T00:00:00Z",
                    prop_nr="P813",
                )
            )
            claims_json = item.claims.get_json()
            for claim in claims_json:
                if claims_json[claim][0]["mainsnak"]["property"] == "P592":
                    chembl_id = claims_json[claim][0]["mainsnak"]["datavalue"]["value"]

            open_targets_reference.add(
                datatypes.URL(
                    f"https://platform.opentargets.org/drug/{chembl_id}",
                    prop_nr="P854",
                )
            )
            all_references.add(open_targets_reference)
            # Update the item on Wikidata
            claim = datatypes.Item(
                prop_nr="P129",
                value=obj_wd,
                qualifiers=qualifiers,
                references=all_references,
            )

            item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)

            object_item = wbi.item.get(entity_id=obj_wd)
            inverse_qualifiers = Qualifiers()
            inverse_qualifiers.add(
                datatypes.Item(prop_nr="P3831", value=action_wd)
            )  # Adding the qualifier from the dictionary

            # Update the item on Wikidata
            inverse_claim = datatypes.Item(
                prop_nr="P129",
                value=subj_wd,
                qualifiers=inverse_qualifiers,
                references=all_references,
            )
            object_item.claims.add(
                inverse_claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE
            )
            object_item.write(
                summary="Update physical interactions from Open Targets.",
            )

    item.write(summary="Update physical interactions from Open Targets.")
    flag += 1
    if flag == 40:
        quit()
