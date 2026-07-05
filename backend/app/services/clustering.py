"""Greedy agglomerative clustering of face embeddings within one event.

Simple and dependency-free: assign each face to the first cluster whose
centroid is within the similarity threshold; otherwise start a new cluster.
Good enough to show organizers "N unique people found".
"""
import numpy as np

SIM_THRESHOLD = 0.55


def cluster_embeddings(ids: list[str], vectors: list[list[float]]) -> dict[str, int]:
    centroids: list[np.ndarray] = []
    counts: list[int] = []
    assignment: dict[str, int] = {}

    for fid, vec in zip(ids, vectors):
        v = np.asarray(vec, dtype=np.float32)
        v = v / (np.linalg.norm(v) + 1e-9)
        best, best_sim = -1, SIM_THRESHOLD
        for i, c in enumerate(centroids):
            sim = float(np.dot(v, c / (np.linalg.norm(c) + 1e-9)))
            if sim > best_sim:
                best, best_sim = i, sim
        if best == -1:
            centroids.append(v.copy())
            counts.append(1)
            assignment[fid] = len(centroids) - 1
        else:
            centroids[best] = (centroids[best] * counts[best] + v) / (counts[best] + 1)
            counts[best] += 1
            assignment[fid] = best
    return assignment
