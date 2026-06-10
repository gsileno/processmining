from collections import defaultdict
from petrinet import PetriNet  # Import shared structure

def alpha_miner(event_log):
    # Step 1: Get all unique activities
    activities = sorted(list(set(act for trace in event_log for act in trace)))

    # Step 2: Identify start and end activities
    start_activities = set(trace[0] for trace in event_log)
    end_activities = set(trace[-1] for trace in event_log)

    # Step 3: Find Direct Succession (A > B)
    direct_succession = set()
    for trace in event_log:
        for i in range(len(trace) - 1):
            direct_succession.add((trace[i], trace[i + 1]))

    # Step 4: Derive Footprint Matrix Relationships
    matrix = defaultdict(dict)
    for a in activities:
        for b in activities:
            a_follows_b = (b, a) in direct_succession
            b_follows_a = (a, b) in direct_succession

            if b_follows_a and a_follows_b:
                matrix[a][b] = "||"
            elif b_follows_a and not a_follows_b:
                matrix[a][b] = "->"
            elif not b_follows_a and a_follows_b:
                matrix[a][b] = "<-"
            else:
                matrix[a][b] = "# "

    # --- Step 5: Convert Matrix to Petri Net ---
    net = PetriNet("Alpha Miner Petri Net")
    p_in = net.add_place("p_start")
    p_out = net.add_place("p_end")
    net.start_place = p_in
    net.end_place = p_out

    for act in activities:
        net.add_transition(act)

    for sa in start_activities:
        net.add_arc(p_in, sa)
    for ea in end_activities:
        net.add_arc(ea, p_out)

    place_counter = 1
    for a in activities:
        for b in activities:
            if matrix[a][b] == "->":
                p_name = f"p_{place_counter}"
                net.add_place(p_name)
                net.add_arc(a, p_name)
                net.add_arc(p_name, b)
                place_counter += 1

    return net

if __name__ == "__main__":
    mock_event_log = [
        ["A", "B", "C", "D"],
        ["A", "B", "C", "D"],
        ["A", "C", "B", "D"],
    ]
    petri_net = alpha_miner(mock_event_log)
    petri_net.display()