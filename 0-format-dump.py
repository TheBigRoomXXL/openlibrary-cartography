""" This script convert Open Library txt files into smaller csv files which are 
easier to load into the db. 

Before reunning the script don't forget to set the input_file, output_folder.
start_line and end_line can be usefull if the script has been interrupted.

You can also rewrite is_valid_row and process_row to change the way the data is preprocessed

This script was derived from :
https://github.com/LibrariesHacked/openlibrary-search/blob/main/openlibrary-data-chunk-process.py"""

import csv
import ctypes as ct
import json

# Inputs to set
input_file = "data/dump.txt"
output_file = "data/0-formated-books.csv"
log_chunk_size = 500_000


# If file size is too big we get _csv.Error: field larger than field limit (131072)
# See https://stackoverflow.com/a/54517228 for more info on this.
csv.field_size_limit(int(ct.c_ulong(-1).value // 2))


def process_row(row: list[str]) -> list:
    """Process a row from the input file and return a list to write.
    Usefull to preprocess and filter the data."""
    if len(row) < 4:
        return False

    original = json.loads(row[4])
    json_doc = {}

    title = original.get("title")
    if title is None:
        return False

    description = get_description(original)
    if not description:
        return False

    authors = get_authors(original)
    if authors:
        json_doc["authors"] = authors

    if original.get("subtitle"):
        json_doc["subtitle"] = original["subtitle"]

    if original.get("subjects"):
        json_doc["subjects"] = original["subjects"]

    if original.get("first_publish_date"):
        json_doc["first_publish_date"] = original["first_publish_date"]

    if original.get("dewey_number"):
        json_doc["dewey_number"] = original["dewey_number"]

    if original.get("covers"):
        json_doc["covers"] = original["covers"]

    json_doc_str = json.dumps(json_doc)

    return [row[1], title, description, json_doc_str]


def get_authors(row: dict) -> list[str] | bool:
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

    return list(keys)


def get_description(row: dict) -> str | bool:
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


with open(output_file, "w", encoding="utf-8") as outputfile:
    csvwriter = csv.writer(
        outputfile,
        delimiter="\t",
        quotechar="|",
        quoting=csv.QUOTE_MINIMAL,
    )
    i = 0  # Number of written line
    with open(input_file, "r", encoding="utf-8") as cvsinputfile:
        csvreader = csv.reader(cvsinputfile, delimiter="\t")
        for linenb, row in enumerate(csvreader):
            if linenb % log_chunk_size == 0:
                print(f"Line {linenb} processed, {i} lines written")

            #  Write the row to the file if there are well formated
            result = process_row(row)
            if result:
                csvwriter.writerow(result)
                i += 1

print("Process complete:")
print("    ", linenb, " works processed")
print("    ", i, " works saved")
