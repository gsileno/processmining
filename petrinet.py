import os
from graphviz import Digraph


class PetriNet:

    def __init__(self, name="Petri Net"):
        self.name = name
        self.places = set()
        self.transitions = set()  # Can include silent transitions 'τ'
        self.arcs = set()  # Set of (source, target) tuples
        self.start_place = None
        self.end_place = None

    def add_place(self, name):
        self.places.add(name)
        return name

    def add_transition(self, name):
        self.transitions.add(name)
        return name

    def add_arc(self, source, target):
        self.arcs.add((source, target))

    def __str__(self):        
        lines = [f"\n=== {self.name} ==="]
        lines.append(f"Places: {sorted(list(self.places))}")
        lines.append(f"Transitions: {sorted(list(self.transitions))}")
        lines.append("Arcs:")
        for src, tgt in sorted(list(self.arcs)):
            lines.append(f"  {src} -> {tgt}")
        return "\n".join(lines)

    def display(self, filename="petri_net_output", view=True):
        """Generates, saves, and opens a visual rendering of the Petri Net
        using Graphviz.
        """
        # Initialize a directed graph with horizontal layout (Left to Right)
        dot = Digraph(self.name, comment=self.name)
        dot.attr(rankdir="LR", engine="dot")

        # 1. Draw Places (Circles)
        for place in self.places:
            # Highlight start/end places with thicker borders
            if place in (self.start_place, "p_start"):
                dot.node(
                    place,
                    label="",
                    shape="circle",
                    style="filled,bold",
                    fillcolor="#e1f5fe",
                    width="0.4",
                )
            elif place in (self.end_place, "p_end"):
                dot.node(
                    place,
                    label="",
                    shape="circle",
                    style="filled,bold",
                    fillcolor="#ffe0b2",
                    width="0.4",
                )
            else:
                dot.node(place, label="", shape="circle", width="0.3")

        # 2. Draw Transitions (Boxes)
        for trans in self.transitions:
            # Draw silent/tau transitions as slim black rectangles
            if "τ" in trans or "tau" in trans.lower():
                dot.node(
                    trans,
                    label="",
                    shape="box",
                    style="filled",
                    fillcolor="black",
                    width="0.15",
                    height="0.4",
                )
            else:
                dot.node(
                    trans,
                    label=trans,
                    shape="box",
                    style="filled",
                    fillcolor="#f5f5f5",
                    height="0.4",
                    width="0.6",
                )

        # 3. Draw Directed Arcs
        for src, tgt in self.arcs:
            dot.edge(src, tgt)

        # Render out the graph image
        try:
            dot.render(filename, format="png", cleanup=True, view=view)           
            print(f"Visual graph successfully saved to: {filename}.png")
        except Exception as e:
            print(
                f"Could not render Graphviz image. (Is the Graphviz system binary installed?): {e}"
            )


# Simple verify block to test local visualization
if __name__ == "__main__":
    net = PetriNet("Test Network")
    net.add_place("p_start")
    net.add_transition("A")
    net.add_place("p1")
    net.add_transition("τ_1")
    net.add_place("p_end")

    net.add_arc("p_start", "A")
    net.add_arc("A", "p1")
    net.add_arc("p1", "τ_1")
    net.add_arc("τ_1", "p_end")

    # This invokes the __str__ conversion method
    print(net)

    # This renders the visual graph layout
    net.display(view=True)
