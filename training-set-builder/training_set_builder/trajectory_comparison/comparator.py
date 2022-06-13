import training_set_builder.trajectory_comparison.sspd as sspd

methods = {
    "sspd": sspd
}


def most_similar_trajectory(comparator, trajectories, method="SSPD"):
    return methods[method.lower()].most_similar_trajectory(comparator, trajectories)
