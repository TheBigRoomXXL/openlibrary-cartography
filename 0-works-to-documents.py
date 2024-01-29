""" This script convert Open Library txt files into a normalized tsv

Before reunning the script don't forget to set input_file, authors_file 
and output_file.

You can easily process_row to fit your own need regarding document schema.

This script was derived from :
https://github.com/LibrariesHacked/openlibrary-search/blob/main/openlibrary-data-chunk-process.py"""

import csv
import json
from ctypes import c_ulong
from typing import Union

# Inputs to set
input_file = "data/unprocessed/dump-works.txt"
authors_file = "data/unprocessed/dump-authors.txt"
output_file = "data/books.tsv"
log_chunk_size = 100_000
start_line = 0

authors_map = {}


# If file size is too big we get _csv.Error: field larger than field limit (131072)
# See https://stackoverflow.com/a/54517228 for more info on this.
csv.field_size_limit(int(c_ulong(-1).value // 2))


def load_authors_in_memory():
    print("loading authors in memory")
    with open(authors_file, "r", encoding="utf-8") as authorcsv:
        csvreader = csv.reader(authorcsv, delimiter="\t")
        for i, row in enumerate(csvreader):
            if i % log_chunk_size == 0:
                print(f"{i:,} authors processed, {len(authors_map):,} names founded")
            if len(row) >= 5:
                data = json.loads(row[4])
                if data.get("name"):
                    authors_map[row[1]] = data["name"]


def process_row(row: list[str]) -> Union[dict, bool]:
    """Process a row from the input file and return it as a document.
    return False instead if the row is not valid"""
    if len(row) < 4:
        return False

    original = json.loads(row[4])
    document = {
        "id": row[1],
    }

    title = original.get("title")
    if title is None:
        return False
    document["title"] = title

    description = get_description(original)
    if not description:
        return False
    document["description"] = description

    authors = get_authors(original)
    if not authors:
        return False
    document["authors"] = authors

    if original.get("subtitle"):
        document["subtitle"] = original["subtitle"]
    else:
        document["subtitle"] = ""

    if original.get("covers"):
        document["covers"] = ";".join([str(cov) for cov in original["covers"]])
    else:
        document["covers"] = ""

    return document


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

    authors_names = [authors_map[k] for k in keys if k in authors_map]

    if len(authors_names) == 0:
        return False

    return ";".join(authors_names)


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


def main():
    w = 0  # Number of written line
    load_authors_in_memory()  # That take bloody long!

    with open(output_file, "w", encoding="utf-8") as csvoutputfile:
        csvwriter = csv.writer(csvoutputfile, delimiter="\t")

        with open(input_file, "r", encoding="utf-8") as cvsinputfile:
            csvreader = csv.reader(cvsinputfile, delimiter="\t")
            for i, row in enumerate(csvreader):
                if i < start_line:
                    continue

                if i % log_chunk_size == 0:
                    print(f"{i:,} works processed, kept {w:,}")

                document = process_row(row)
                if not document:
                    continue

                csvwriter.writerow(document.values())
                w += 1

    print("Process complete:")
    print("    ", i, " works processed")
    print("    ", w, " works saved")


if __name__ == "__main__":
    main()
