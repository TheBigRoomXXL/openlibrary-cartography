""" This take the csv from the script 0-format-dump.py and add the embeddings at the end of each line.

Use start_line if the script has been interrupted.
"""

import csv
import ctypes as ct
import json
from base64 import b64encode
from io import BytesIO

import torch
from compel import Compel, ReturnedEmbeddingsType  # to deal with long prompts
from diffusers import DiffusionPipeline

# Inputs to set
input_path = "data/0-formated-books.csv"
output_path = "data/1-formated-books-with-embeddings.csv"
start_line = 0


# If file size is too big we get _csv.Error: field larger than field limit (131072)
# See https://stackoverflow.com/a/54517228 for more info on this.
csv.field_size_limit(int(ct.c_ulong(-1).value // 2))


def prepare_compel():
    """Prepare the pipeline to get the embeddings"""
    pipeline = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        use_safetensors=True,
        torch_dtype=torch.float32,
    )

    compel = Compel(
        tokenizer=pipeline.tokenizer_2,
        text_encoder=pipeline.text_encoder_2,
        truncate_long_prompts=False,
        requires_pooled=True,
        returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
    )

    return compel


def get_prompt(row: list) -> str:
    """Assemble the row interesting data into a prompt"""
    title = row[1]
    description = row[2]
    metadata = json.loads(row[3])

    subjects_list = metadata.get("subjects")
    if subjects_list:
        subjects = " ".join(subjects_list)
    else:
        subjects = ""

    return f"{title} {description} {subjects}"


def embeddings_to_b64_string(embedding: torch.Tensor) -> str:
    """Okay, I know base64 is not the best way to store the embeddings, but it's
    the easiest way to store them in a csv file and csv make the data processing simple."""
    buffer = BytesIO()
    torch.save(embedding, buffer)
    return b64encode(buffer.getvalue()).decode()


print("Preparing model")
compel = prepare_compel()
print()

print("Starting to process data")
with open(output_path, "w", encoding="utf-8") as outputfile:
    csvwriter = csv.writer(
        outputfile,
        delimiter="\t",
        quotechar="|",
        quoting=csv.QUOTE_MINIMAL,
    )

    with open(input_path, "r", encoding="utf-8") as inputfile:
        csvreader = csv.reader(
            inputfile,
            delimiter="\t",
            quotechar="|",
            quoting=csv.QUOTE_MINIMAL,
        )
        for i, row in enumerate(csvreader):
            if i < start_line:
                continue

            print(f"Processing line {i} ")

            prompt = get_prompt(row)
            embedding = compel(prompt)
            embedding_b64 = embeddings_to_b64_string(embedding)

            if len(row) > 4:
                row[4] = embedding_b64
            else:
                row.append(embedding_b64)

            csvwriter.writerow(row)

print("Process complete. Total lines:", i)
