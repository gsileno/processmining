from petrinet import PetriNet

def evaluate_petri_net(petri_net, log):
    """Calculates Token-Based Fitness, Tracking Coverage, and Behavioral Precision
    for a given PetriNet against an event log using token replay mechanism.
    
    Returns a dictionary of conformance metrics.
    """
    total_produced = 0
    total_consumed = 0
    total_missing = 0
    total_remaining = 0
    
    # Track metrics for precision
    total_enabled_transitions = 0
    total_fired_transitions = 0
    
    # Helper to find transitions associated with an activity name or silent step
    def get_transitions_for_activity(act):
        return [t for t in petri_net.transitions if t == act]
    
    def get_enabled_transitions(marking):
        # A transition is enabled if all its input places have at least 1 token
        enabled = []
        for t in petri_net.transitions:
            # Find input places for transition t
            inputs = [src for (src, tgt) in petri_net.arcs if tgt == t]
            if inputs and all(marking.get(p, 0) > 0 for p in inputs):
                enabled.append(t)
        return enabled

    # Replay every trace in the log
    for trace in log:
        # Initialize marking with 1 token in the start place
        marking = {petri_net.start_place: 1}
        
        # Local metrics for this trace
        produced = 1  # Started with 1
        consumed = 0
        missing = 0
        remaining = 0
        
        for activity in trace:
            # 1. Check enabled transitions to calculate precision metrics later
            enabled_now = get_enabled_transitions(marking)
            total_enabled_transitions += len(enabled_now)
            total_fired_transitions += 1
            
            # Find the transition matching this log activity
            target_transitions = get_transitions_for_activity(activity)
            if not target_transitions:
                # The activity doesn't even exist in the net layout
                continue
                
            t_to_fire = target_transitions[0]
            inputs = [src for (src, tgt) in petri_net.arcs if tgt == t_to_fire]
            outputs = [tgt for (src, tgt) in petri_net.arcs if src == t_to_fire]
            
            # 2. Consume tokens from input places
            for p_in in inputs:
                if marking.get(p_in, 0) > 0:
                    marking[p_in] -= 1
                    consumed += 1
                else:
                    # Token missing! Force it so simulation can continue
                    missing += 1
                    consumed += 1
                    
            # 3. Produce tokens into output places
            for p_out in outputs:
                marking[p_out] = marking.get(p_out, 0) + 1
                produced += 1
                
        # 4. Finalize trace: Consume the token from the end place
        if marking.get(petri_net.end_place, 0) > 0:
            marking[petri_net.end_place] -= 1
            consumed += 1
        else:
            missing += 1
            consumed += 1
            
        # Any tokens left over in the net are remaining/deadlocks
        remaining += sum(marking.values())
        
        # Accumulate global values
        total_produced += produced
        total_consumed += consumed
        total_missing += missing
        total_remaining += remaining

    # --- METRIC MATHEMATICAL CALCULATIONS ---
    
    # 1. Token-Based Fitness (Alignment/Accuracy)
    # Balanced formula between missing/consumed tokens and remaining/produced tokens
    fitness = 0.5 * (1 - (total_missing / total_consumed)) + 0.5 * (1 - (total_remaining / total_produced))
    
    # 2. Trace Coverage
    # Percentage of traces that ran completely without a single missing token
    # (Simulated simple proxy via token ratio here)
    coverage = 1.0 - (total_missing / total_consumed)
    
    # 3. Behavioral Precision
    # Measures how "tight" the model is. High precision means the model rarely 
    # activates transitions that the log never actually executes.
    precision = (total_fired_transitions / total_enabled_transitions) if total_enabled_transitions > 0 else 0.0

    return {
        "Token Fitness (Accuracy)": round(fitness, 4),
        "Log Trace Coverage": round(max(0.0, coverage), 4),
        "Behavioral Precision": round(precision, 4),
        "Diagnostics": {
            "Total Produced Tokens": total_produced,
            "Total Consumed Tokens": total_consumed,
            "Missing Tokens (Errors)": total_missing,
            "Leftover Tokens (Deadlocks)": total_remaining
        }
    }

def calculate_simplicity_metrics(petri_net):
    """Computes structural simplicity metrics for a given PetriNet object."""
    num_places = len(petri_net.places)
    num_transitions = len(petri_net.transitions)
    num_arcs = len(petri_net.arcs)
    
    # 1. Total Graph Size (Elements count: Arcs + Places + Transitions)
    graph_size = num_places + num_transitions + num_arcs
    
    # 2. Graph Density Metric
    # Density = |A| / (|P| * |T|). High density implies an unreadable, over-connected net.
    max_possible_connections = num_places * num_transitions
    density = num_arcs / max_possible_connections if max_possible_connections > 0 else 0.0
    
    # 3. McCabe Cyclomatic Complexity 
    # Assumes a single connected component (connected_components = 1)
    cyclomatic_complexity = num_arcs - (num_places + num_transitions) + 2
    
    # 4. Control-Flow Complexity (CFC Proxy via Transition degrees)
    cfc_score = 0
    for trans in petri_net.transitions:
        # Count output arcs originating from this specific transition
        outputs = sum(1 for (src, tgt) in petri_net.arcs if src == trans)
        if outputs > 1:
            cfc_score += (outputs - 1) ** 2
            
    return {
        "Structural Size": graph_size,
        "Graph Density": round(density, 4),
        "Cyclomatic Complexity (Loops/Paths)": cyclomatic_complexity,
        "Control-Flow Complexity (Splits)": cfc_score
    }
    
if __name__ == "__main__":
    # ---------------------------------------------------------
    # 1. Manually Assemble a Petri Net Structures
    # ---------------------------------------------------------

    # Process Flow: A -> [B or C] -> D

    net = PetriNet("Manual Test Network")
    p_start = net.add_place("p_start")
    p1 = net.add_place("pi_1")
    p2 = net.add_place("pi_2")
    p_end = net.add_place("p_end")   
    net.end_place = p_end   
    net.add_transition("A")
    net.add_transition("B")
    net.add_transition("C")
    net.add_transition("D")
    net.add_arc(p_start, "A")
    net.add_arc("A", p1)
    net.add_arc(p1, "B")
    net.add_arc(p1, "C")        
    net.add_arc("B", p2)
    net.add_arc("C", p2)
    net.add_arc(p2, "D")
    net.add_arc("D", p_end)
        
    # ---------------------------------------------------------
    # 2. Define a Test Log with Various Conformance Scenarios
    # ---------------------------------------------------------
    test_log = [
        ["A", "B", "D"],       # 1. Perfect standard trace (using route B)
        ["A", "C", "D"],       # 2. Perfect standard trace (using route C)
        ["A", "B", "D"],       # 3. Repeated clean execution
        ["A", "B", "C", "D"],  # 4. Non-compliant trace (executed BOTH options instead of choice)
        ["A", "D"]             # 5. Missing trace (skipped the middle steps entirely)
    ]
    
    # ---------------------------------------------------------
    # 3. Run the Evaluation Suite
    # ---------------------------------------------------------
    print("\n--- Running Conformance Token Replay ---")
    results = evaluate_petri_net(net, test_log)
    for metric, value in results["Diagnostics"].items():
        print(f" - {metric}: {value}")
    
    print("\n=== BEHAVIOURAL METRICS =======================================")
    print(f"Token Fitness (Accuracy): {results['Token Fitness (Accuracy)'] * 100}%")
    print(f"Log Trace Coverage:       {results['Log Trace Coverage'] * 100}%")
    print(f"Behavioral Precision:     {results['Behavioral Precision'] * 100}%")
    

	# ---------------------------------------------------------
    # 4. Run the Structural Simplicity Diagnostics
    # ---------------------------------------------------------
    print("\n=== SIMPLICITY METRICS ========================================")
    simplicity_results = calculate_simplicity_metrics(net)
    
    print(f"Structural Size Metric:      {simplicity_results['Structural Size']} elements")
    print(f"Graph Density:               {simplicity_results['Graph Density'] * 100}%")
    print(f"Cyclomatic Complexity:       {simplicity_results['Cyclomatic Complexity (Loops/Paths)']}")
    print(f"Control-Flow Complexity:     {simplicity_results['Control-Flow Complexity (Splits)']}")
