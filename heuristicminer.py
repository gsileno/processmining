from collections import Counter, defaultdict
from petrinet import PetriNet  # Import shared structure

def heuristic_miner(event_log, threshold=0.5):
    succession_counts = Counter()
    all_activities = set()

    for trace in event_log:
        for act in trace:
            all_activities.add(act)
        for i in range(len(trace) - 1):
            succession_counts[(trace[i], trace[i + 1])] += 1

    activities = sorted(list(all_activities))
    dependencies = defaultdict(dict)

    for a in activities:
        for b in activities:
            ab_count = succession_counts[(a, b)]
            ba_count = succession_counts[(b, a)]

            if a == b:
                score = ab_count / (ab_count + 1)
            else:
                score = (ab_count - ba_count) / (ab_count + ba_count + 1)

            dependencies[a][b] = round(score, 2)

    # --- Convert Causal Relations to Petri Net ---
    net = PetriNet("Heuristics Miner Petri Net")
    for act in activities:
        net.add_transition(act)

    has_incoming = {act: False for act in activities}
    has_outgoing = {act: False for act in activities}
    causal_arcs = []

    for a in activities:
        for b in activities:
            if dependencies[a][b] >= threshold:
                causal_arcs.append((a, b))
                has_outgoing[a] = True
                has_incoming[b] = True

    p_start = net.add_place("p_start")
    p_end = net.add_place("p_end")
    net.start_place = p_start
    net.end_place = p_end

    for act in activities:
        if not has_incoming[act]:
            net.add_arc(p_start, act)
        if not has_outgoing[act]:
            net.add_arc(act, p_end)

    for idx, (a, b) in enumerate(causal_arcs):
        p_name = f"p_causal_{idx+1}"
        net.add_place(p_name)
        net.add_arc(a, p_name)
        net.add_arc(p_name, b)

    return net

if __name__ == "__main__":
    noisy_log = [
        ["A", "B", "C", "D"],
        ["A", "B", "C", "D"],
        ["A", "B", "C", "D"],
        ["A", "C", "B", "D"],
    ]
    petri_net = heuristic_miner(noisy_log, threshold=0.5)
    petri_net.display()