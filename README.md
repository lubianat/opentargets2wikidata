# OpenTargets2Wikidata

## Introduction

OpenTargets2Wikidata is a tool designed to integrate Open Targets data into Wikidata. This repository contains the source code, data files, and documentation needed to achieve this integration.

## Features

- Data fetching from Open Targets platform
- Data transformation into Wikidata-compatible formats
- Error logging and unmatched ChEMBL IDs tracking

## Requirements

- Python 3.8+
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

To install the required dependencies, follow these steps:

1. Clone the repository
   ```bash
   git clone https://github.com/lubianat/opentargets2wikidata.git
   ```
2. Navigate to the project directory
   ```bash
   cd opentargets2wikidata
   ```
3. Install dependencies using Poetry
   ```bash
   poetry install
   ```

## Usage

1. Fetch the data
   ```bash
   python src/fetch_data.py
   ```
2. Transform the data
   ```bash
   python src/transform_data.py
   ```
3. Upload the data to Wikidata
   ```bash
   python src/upload_to_wikidata.py
   ```

## Contributing

Please read `.github/CONTRIBUTING.md` for details on our code of conduct, and the process for submitting pull requests.

## Acknowledgments

- Open Targets Platform for providing the data
- Wikidata community for the support