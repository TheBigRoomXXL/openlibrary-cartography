""" This script import documents from a tsv file into chromaDb. 

Before reunning the script don't forget to set input_file, authors_file 
and output_file.

This script will restart where it last stopped. Reset the collection first if 
you want to re-import everything.

"""

import csv
from time import perf_counter
from ctypes import c_ulong

import chromadb

# Inputs to set
input_file = "data/books.tsv"
log_chunk_size = 100


# If file size is too big we get _csv.Error: field larger than field limit (131072)
# See https://stackoverflow.com/a/54517228 for more info on this.
csv.field_size_limit(int(c_ulong(-1).value // 2))


def get_row_as_prompt(row: list[str]) -> str:
    """Assemble the document data into a prompt"""
    title = row[1]
    description = row[2]
    authors = row[3]
    subtitle = row[4]

    return f"{title}, {subtitle} by {authors.replace(';', ', ')}: {description}"


def get_row_as_metadata(row:list[str])-> dict:
    """Assemble the document into a dictionary for later reference"""
    return {
        "title" : row[1],
        "description" : row[2],
        "authors" : row[3],
        "subtitle" : row[4],
        "covers" : row[0],
    }

def main():
    t0 = perf_counter()
    client = chromadb.PersistentClient(path="data/books.db")
    col = client.get_or_create_collection(
        name="books-all-MiniLM-L6-v2-l2",  
    )

    start_line = col.count() # restart where we left


    with open(input_file, "r", encoding="utf-8") as cvsinputfile:
        csvreader = csv.reader(cvsinputfile, delimiter="\t")
        for i, row in enumerate(csvreader):
            if i < start_line:
                continue

            if i % log_chunk_size == 0:
                print(f"{i:,} works processed in {round(perf_counter() - t0)}s")

            key = row[0]
            prompt = get_row_as_prompt(row)
            metadata = get_row_as_metadata(row)
            col.add(documents=prompt, metadatas=metadata, ids=key)

    print("Process complete:")
    print("    ", i, " works processed")


if __name__ == "__main__":
    main()
