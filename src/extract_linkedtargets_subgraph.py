import csv
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent.resolve()
DATA = HERE.parent.joinpath("data").resolve()
RESULTS = HERE.parent.joinpath("results").resolve()


def write_tsv(output_file, rows):
    with output_file.open("w", newline="") as tsvfile:
        tsv_writer = csv.writer(tsvfile, delimiter="\t")
        tsv_writer.writerow(["id", "linkedTargets"])
        for row in rows:
            tsv_writer.writerow(row)


def extract_linked_targets(molecule_dir):
    rows = []
    for parquet_file in molecule_dir.glob("*.snappy.parquet"):
        df = pd.read_parquet(parquet_file)
        print(df.columns)
        for index, row in df.iterrows():
            linked_targets = row["linkedTargets"]
            id = row["id"]
            if linked_targets is not None:
                linked_target_list = linked_targets["rows"]
                for target in linked_target_list:
                    rows.append([id, target])
    return rows


def main():
    output_file = RESULTS / "linkedTargets.tsv"
    molecule_dir = DATA / "molecule"
    rows = extract_linked_targets(molecule_dir)
    write_tsv(output_file, rows)


if __name__ == "__main__":
    main()
