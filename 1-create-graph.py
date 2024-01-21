import chromadb
import numpy as np
from matplotlib import pyplot as plt
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform


def print_graph(distance_matrix, links):
    """Print data as graph"""

    fig, ax = plt.subplots(1, 2)

    # Distance matrix
    ax[0].imshow(distance_matrix)
    ax[0].set_title("Distance")
    ax[0].set_xlabel("Prompts")
    ax[0].set_ylabel("Prompts")
    ax[0].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for spine in ax[0].spines.values():
        spine.set_visible(False)

    # Dendrogram
    ax[1].set_xlabel("ward", fontdict={"size": 12})
    hierarchy.dendrogram(
        links,
        orientation="left",
        no_labels=True,
        ax=ax[1],
    )

    plt.show()


def map_cluster(
    cluster: int, depth: int, clusters_levels: list[list[int]], ids: list[str]
):
    level = clusters_levels[depth]
    cluster_indexs = [i for i, c in enumerate(level) if c == cluster]

    # Base case:  we are at the book level
    if depth == len(clusters_levels) - 1:
        books = list(set([key for i, key in enumerate(ids) if i in cluster_indexs]))
        return {"name": f"{depth}-{cluster}", "children": books}

    # Recursive case, we go deeper
    level_bellow = clusters_levels[depth + 1]
    cluster_to_map = list(
        set([c for i, c in enumerate(level_bellow) if i in cluster_indexs])
    )

    return {
        "name": f"{depth}-{cluster}",
        "children": [
            map_cluster(c, depth + 1, clusters_levels) for c in cluster_to_map
        ],
    }


def main():
    print("Process start")
    client = chromadb.PersistentClient(path="books.chromadb")
    collection = client.get_collection(name="books")

    #  Extracting enbeddings
    docs = collection.get(include=["embeddings"], limit=10000)
    enbeddings = np.asarray(docs["embeddings"])
    ids = docs["ids"]

    # Calculate distance matrix
    distance_matrix = np.matmul(enbeddings, enbeddings.T)  # cosine score
    np.fill_diagonal(distance_matrix, 1.0)  # force precision
    distance_matrix = np.clip(distance_matrix, -1, 1)  # force precision
    distance_matrix = np.rad2deg(np.arccos(distance_matrix))  # work in degree
    distance_matrix = (distance_matrix + distance_matrix.T) / 2  # force precision

    # Compute hierarchical structure
    sqf = squareform(distance_matrix)
    links = hierarchy.linkage(sqf, method="ward")

    print_graph(distance_matrix, links)

    #  Multi level clustering
    factors = [0.5, 0.15, 0.01]
    lmax = links[:, 2].max()

    levels = [
        hierarchy.fcluster(links, t=f * lmax, criterion="distance") for f in factors
    ]

    print("Process complete:")


if __name__ == "__main__":
    main()
