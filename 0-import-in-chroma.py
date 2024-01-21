""" This script convert Open Library txt files into smaller csv files which are 
easier to load into the db. 

Before reunning the script don't forget to set the input_file, output_folder.
start_line and end_line can be usefull if the script has been interrupted.

You can also rewrite is_valid_row and process_row to change the way the data is preprocessed

This script was derived from :
https://github.com/LibrariesHacked/openlibrary-search/blob/main/openlibrary-data-chunk-process.py"""

import csv
import json
from ctypes import c_ulong
from time import perf_counter
from typing import Union

import chromadb

# Inputs to set
input_file = "data/dump.txt"
log_chunk_size = 5000
start_line = 1050000


# If file size is too big we get _csv.Error: field larger than field limit (131072)
# See https://stackoverflow.com/a/54517228 for more info on this.
csv.field_size_limit(int(c_ulong(-1).value // 2))


def process_row(row: list[str]) -> Union[dict, bool]:
    """Process a row from the input file and return a list to write.
    return False if the row is not valid"""
    if len(row) < 4:
        return False

    original = json.loads(row[4])
    metadata = {
        "id": row[1],
    }

    title = original.get("title")
    if title is None:
        return False
    metadata["title"] = title

    description = get_description(original)
    if not description:
        return False
    metadata["description"] = description

    authors = get_authors(original)
    if authors:
        metadata["authors"] = authors

    if original.get("subtitle"):
        metadata["subtitle"] = original["subtitle"]

    if original.get("subjects"):
        metadata["subjects"] = " ".join(original["subjects"])

    if original.get("first_publish_date"):
        metadata["first_publish_date"] = original["first_publish_date"]

    if original.get("dewey_number"):
        metadata["dewey_number"] = " ".join(original["dewey_number"])

    if original.get("covers"):
        metadata["covers"] = " ".join([str(cov) for cov in original["covers"]])

    return metadata


def get_authors(row: dict) -> Union[list[str], bool]:
    """Simplify the authors list to only keep the author key.
    Return False if there is no author or no key"""
    authors = row.get("authors")
    if not authors or len(authors) == 0:
        return False

    keys = set()
    for obj in authors:
        author = obj.get("author")
        if author is None:
            continue

        if isinstance(author, str):
            keys.add(author)
            continue

        key = author.get("key")
        if key is None:
            continue
        keys.add(key)

    if len(keys) == 0:
        return False

    return " ".join(keys)


def get_description(row: dict) -> Union[str, bool]:
    """Simplify the description as a string instread of an object.
    Return False if there is no description or no value"""
    description_obj = row.get("description")
    if not description_obj:
        return False

    if isinstance(description_obj, str):
        return description_obj

    value = description_obj.get("value")
    if value is None:
        return False

    return value


def get_prompt(metadata: list) -> str:
    """Assemble the metadata interesting data into a prompt"""
    title = metadata["title"]
    description = metadata["description"]

    subjects_list = metadata.get("subjects")
    if subjects_list:
        subjects = " ".join(subjects_list)
    else:
        subjects = ""

    return f"{title} {description} {subjects}"


def main():
    i = 0  # Number of written line
    client = chromadb.PersistentClient(path="books.chromadb")
    collection = client.get_or_create_collection(name="books")
    t0 = perf_counter()
    with open(input_file, "r", encoding="utf-8") as cvsinputfile:
        csvreader = csv.reader(cvsinputfile, delimiter="\t")
        for linenb, row in enumerate(csvreader):
            if linenb < start_line:
                continue

            if linenb % log_chunk_size == 0:
                print(
                    f"{linenb-start_line} lines processed, {i} lines written, in {perf_counter()-t0} seconds"
                )

            metadata = process_row(row)
            if not metadata:
                continue

            prompt = get_prompt(metadata)
            collection.add(documents=prompt, metadatas=metadata, ids=metadata["id"])
            i += 1

    print("Process complete:")
    print("    ", linenb, " works processed")
    print("    ", i, " works saved")


if __name__ == "__main__":
    main()
