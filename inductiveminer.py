from collections import Counter
from petrinet import PetriNet

def filter_infrequent_activities(log, activities, threshold):
    """Filters out activities that appear below the frequency threshold percent
    relative to the most frequent activity in this sub-log.
    """
    if not log or not activities:
        return set(), []

    counts = Counter(act for trace in log for act in trace if act in activities)
    if not counts:
        return set(), []

    max_freq = max(counts.values())
    cutoff = max_freq * threshold

    valid_activities = {act for act, count in counts.items() if count >= cutoff}

    filtered_log = []
    for trace in log:
        filtered_trace = [act for act in trace if act in valid_activities]
        if filtered_trace:
            filtered_log.append(filtered_trace)

    return valid_activities, filtered_log


def precalculate_relations(log):
    """Pre-calculates structural behavior once for the entire log.
    Returns:
      - comes_before: set of pairs (A, B) where A appeared before B anywhere in a trace.
      - co_occurs: dict mapping each activity to a set of activities it shares a trace with.
    """
    comes_before = set()
    co_occurs = {}

    for trace in log:
        for i, act1 in enumerate(trace):
            if act1 not in co_occurs:
                co_occurs[act1] = set()
            
            for act2 in trace[i:]:
                co_occurs[act1].add(act2)
                if act1 != act2:
                    # Collect every distinct downstream reachability pair
                    for act_later in trace[i+1:]:
                        comes_before.add((act1, act_later))
                        
    return comes_before, co_occurs


def find_sequence_cut(activities, comes_before):
    if len(activities) <= 1:
        return None

    # Topologically count how many active nodes occur before each specific activity
    before_counts = {act: 0 for act in activities}
    for a in activities:
        for b in activities:
            if (a, b) in comes_before:
                before_counts[b] += 1

    # Deterministically sort activities based on data stream topology, NOT alphabet
    topological_order = sorted(list(activities), key=lambda x: before_counts[x])

    # Evaluate the cut frontiers sequentially
    for k in range(1, len(topological_order)):
        candidate_s1 = set(topological_order[:k])
        candidate_s2 = set(topological_order[k:])

        # Valid sequence means NO element in S2 ever fires before an element in S1
        is_valid = True
        for src in candidate_s2:
            for tgt in candidate_s1:
                if (src, tgt) in comes_before:
                    is_valid = False
                    break
            if not is_valid:
                break

        if is_valid:
            return candidate_s1, candidate_s2
    return None


def find_xor_cut(activities, co_occurs):
    if len(activities) <= 1:
        return None

    unvisited = set(activities)
    groups = []

    # Identify non-overlapping structural execution clusters (Connected Components)
    while unvisited:
        start = next(iter(unvisited))
        current_group = set()
        queue = [start]

        while queue:
            node = queue.pop(0)
            if node in unvisited:
                unvisited.remove(node)
                current_group.add(node)
                # Filter shared neighbors to only what remains active in the current sub-problem
                neighbors = co_occurs.get(node, set()) & activities
                for neighbor in neighbors:
                    if neighbor in unvisited:
                        queue.append(neighbor)
        groups.append(current_group)

    if len(groups) <= 1:
        return None

    return groups[0], set().union(*groups[1:])


def find_parallel_cut(activities, comes_before):
    if len(activities) <= 1:
        return None

    def are_parallel(a, b):
        return (a, b) in comes_before and (b, a) in comes_before

    # Isolate independent parallel stream components
    acts = sorted(list(activities))
    g1 = {acts[0]}
    g2 = set()

    for act in acts[1:]:
        if all(are_parallel(act, x) for x in g1):
            g2.add(act)
        else:
            g1.add(act)

    if g1 and g2 and (len(g1) + len(g2) == len(activities)):
        # Verify strict compliance across the bi-graph cuts
        for a in g1:
            for b in g2:
                if not are_parallel(a, b):
                    return None
        return g1, g2
    return None


def inductive_miner_infrequent(log, activities=None, threshold=0.20, relations=None):
    if activities is None:
        activities = set(act for trace in log for act in trace)

    # Initial boot step: compute relationships globally once
    if relations is None:
        relations = precalculate_relations(log)

    comes_before, co_occurs = relations

    # Run structural noise filtering
    activities, log = filter_infrequent_activities(log, activities, threshold)

    if len(activities) == 0:
        return "τ"
    if len(activities) == 1:
        return list(activities)[0]

    # 1. Topological Sequence Cut Check
    seq_cut = find_sequence_cut(activities, comes_before)
    if seq_cut:
        return (
            "→",
            inductive_miner_infrequent(log, seq_cut[0], threshold, relations),
            inductive_miner_infrequent(log, seq_cut[1], threshold, relations),
        )

    # 2. Topological XOR (Choice) Cut Check
    xor_cut = find_xor_cut(activities, co_occurs)
    if xor_cut:
        return (
            "×",
            inductive_miner_infrequent(log, xor_cut[0], threshold, relations),
            inductive_miner_infrequent(log, xor_cut[1], threshold, relations),
        )

    # 3. Topological Parallel Cut Check
    parallel_cut = find_parallel_cut(activities, comes_before)
    if parallel_cut:
        return (
            "∧",
            inductive_miner_infrequent(log, parallel_cut[0], threshold, relations),
            inductive_miner_infrequent(log, parallel_cut[1], threshold, relations),
        )

    # Fallback Loop (Alphabetical sort applied safely here only for fallback visualization stability)
    return ("Fallback-Loop", sorted(list(activities)))


# ==========================================
# 3. COMPONENT GENERATION PARSER
# ==========================================

def convert_tree_to_petri(tree):
    net = PetriNet("Inductive Miner Petri Net")
    p_start = net.add_place("p_start")
    p_end = net.add_place("p_end")
    net.start_place = p_start
    net.end_place = p_end

    place_idx = [0]
    tau_idx = [0]

    def get_new_place():
        place_idx[0] += 1
        return net.add_place(f"pi_{place_idx[0]}")

    def get_new_tau():
        tau_idx[0] += 1
        return net.add_transition(f"τ_{tau_idx[0]}")

    def parse(node, entry_place, exit_place):
        if isinstance(node, str):
            if node == "τ":
                t_silent = get_new_tau()
                net.add_arc(entry_place, t_silent)
                net.add_arc(t_silent, exit_place)
            else:
                net.add_transition(node)
                net.add_arc(entry_place, node)
                net.add_arc(node, exit_place)
            return

        operator = node[0]
        children = node[1:]

        if operator == "→":
            current_entry = entry_place
            for i, child in enumerate(children):
                next_exit = exit_place if i == len(children) - 1 else get_new_place()
                parse(child, current_entry, next_exit)
                current_entry = next_exit

        elif operator == "×":
            for child in children:
                parse(child, entry_place, exit_place)

        elif operator == "∧":
            t_fork = get_new_tau()
            net.add_arc(entry_place, t_fork)
            t_join = get_new_tau()
            net.add_arc(t_join, exit_place)

            for child in children:
                child_entry = get_new_place()
                child_exit = get_new_place()
                net.add_arc(t_fork, child_entry)
                parse(child, child_entry, child_exit)
                net.add_arc(child_exit, t_join)

        # FIX: Fully isolated fallback loops using nested boundaries 
        elif operator == "Fallback-Loop":
            t_enter_loop = get_new_tau()
            t_exit_loop = get_new_tau()
            
            loop_body_entry = get_new_place()
            loop_body_exit = get_new_place()
            
            net.add_arc(entry_place, t_enter_loop)
            net.add_arc(t_enter_loop, loop_body_entry)
            
            net.add_arc(loop_body_exit, t_exit_loop)
            net.add_arc(t_exit_loop, exit_place)
            
            for child in children:
                parse(child, loop_body_entry, loop_body_exit)
                
            t_loop_back = get_new_tau()
            net.add_arc(loop_body_exit, t_loop_back)
            net.add_arc(t_loop_back, loop_body_entry)

    parse(tree, p_start, p_end)
    return net


if __name__ == "__main__":
    # Test Log containing an obvious sequential pattern (A -> B -> D) with an infrequent noise variant
    noisy_log = [
        ["A", "B", "D"],
        ["A", "B", "D"],
        ["A", "B", "D"],
        ["A", "B", "D"],
        ["A", "C", "B", "D"],
    ]

    # Mining with noise filtering active
    process_tree = inductive_miner_infrequent(noisy_log, threshold=0.25)
    print("--- Inductive Miner Infrequent (IMf) Tree ---")
    print(process_tree)

    # Translate structure and visualize
    petri_net = convert_tree_to_petri(process_tree)
    petri_net.display(filename="process_mined_net", view=True)
