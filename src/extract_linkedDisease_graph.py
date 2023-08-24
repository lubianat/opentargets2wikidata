from pyspark.sql import SparkSession
from pathlib import Path
import pandas as pd


def extract_linked_targets(molecule_dir, spark):
    # Reading all parquet files in the directory
    df = spark.read.parquet(str(molecule_dir))

    # Filtering and transforming the data using DataFrame API
    df_filtered = df.filter(df.score > 0.7).select(
        "diseaseId", "targetId", "score", "evidenceCount"
    )

    return df_filtered


def main():
    # Initialize Spark session
    spark = SparkSession.builder.appName("optimize_code").getOrCreate()

    # Define paths
    output_file = (
        "linkedDiseases.tsv"  # This can be modified based on your preferred location
    )
    molecule_dir = Path(__file__).parent.parent / "data" / "associationByOverallDirect"

    # Extract and filter data
    df_filtered = extract_linked_targets(molecule_dir, spark)

    # Convert the Spark DataFrame to a Pandas DataFrame and save it
    df_filtered_pd = df_filtered.toPandas()
    df_filtered_pd.to_csv(output_file, sep="\t", index=False)

    spark.stop()


if __name__ == "__main__":
    main()
