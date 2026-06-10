# Process mining algorithms 

This repository collects simple Python implementations of three process mining algorithms:

- *Alpha Miner*, from [1]
- *Heuristic Miner* (filtering infrequent cases), from [2]
- *Inductive Miner Infrequent* (filtering infrequent cases), from [3]

## Algorithms

### Alpha Miner

Alpha Miner [1] is based primarily the *ordering relations* which map log-based successions to formal process dependencies:
1. *direct succession* ($A > B$): $B$ immediately follows $A$
2. *causality* ($A \rightarrow B$): $A > B$ happens, but never $B > A$.
3. *parallelism* ($A \parallel B$): Both $A > B$ and $B > A$ happen 
4. *choice* or *alternative* ($A \oplus B$):Neither $A > B$ nor $B > A$ ever happen

### Heuristic Miner

While the Alpha Miner is notorious for failing when faced with "noisy" or infrequent data, the Heuristics Miner [2] was explicitly designed to handle noise and exceptions by using frequency and a dependency measure formula. This *dependency score* between two activities $A$ and $B$ is defined as:

$$\text{Dependency}(A \rightarrow B) = \frac{|A > B| - |B > A|}{|A > B| + |B > A| + 1}$$

where $|A > B|$ is the frequency of $B$ directly following $A$.

### Inductive Miner (with Infrequent filter)

The Inductive Miner [3] is a recursive, top-down algorithm, the most complex of the three. It looks at the entire event log, finds the most prominent behavioral pattern, splits the log into smaller pieces based on that pattern, and then repeats the process on those pieces until there is nothing left to split. Its core functioning can be described in 3 steps. First, it looks at the event log and maps out which activities follow each other immediately. If "Activity A" is followed by "Activity B" 50 times, a strong arrow (edge) is drawn between them. This creates a network of activities connected by arrows, or Directly-Follows Graph (DFG). Second, the algorithm detects a *cut*; it analyzes the DFG to see how it can be chopped into independent parts. It looks for four specific types of cuts, which correspond to standard workflow behaviors: 
- *sequence* ($\rightarrow$),
- *exclusive choice* ($\times$ or $\oplus$),
- *parallel* ($\wedge$ or $+$),
- *loop* ($\circlearrowleft$).
Once a cut is detected, the algorithm creates a "node" in the process tree for that operator (e.g., a parallel node). It then splits the event log into sub-logs based on the pieces it just separated. Sometimes, the algorithm can't find a perfect, clean cut because of "noise" or exceptions in the data; it then applies a fallback mechanism. It might forcibly filter out rare paths, or as a last resort, introduce a "flower loop" (which basically says "any of these activities can happen in any order").

Algorithms in the Inductive Miner family guarantee the discovery of *sound* process models (models completely free of deadlocks or livelocks). The specific inductive miner "infrequent" variant introduces a noise-filtering threshold step at each recursion level to strip away infrequent behaviors, making it resilient to real-world messy data.

## Evaluation metrics

The three algorithms provide different types of output which are then converted into a Petri net. Given a Petri net (model) and a log (observations), we can evaluate the model according to several dimensions. In the process mining literature, these are associated to four families:

- *Fitness* (Accuracy/Coverage): Can the Petri Net actually replay the traces observed in the log?
- *Precision*: Does the Petri Net forbid behavior not seen in the log (i.e., is it avoiding over-generalization)?
- *Generalization*: Can the net handle unseen but future related behavior?
- *Simplicity*: Is the model easy to read (Occam's razor principle)?

For the behavioural analysis of the model, here we compute two most critical operational metrics via token replay via simulation: **Trace Fitness** (how much of the log can be parsed) and **Behavioral Precision** (how tight the model's allowed paths are compared to the log) [4, 5, 6]. For the structural analysis of the model, we compute **Structural Size**. **Structural Density**, **Cyclomatic Complexity**, amd **Control-Flow Complexity** (or weighter coupling) [7, 8].

### Trace Fitness

Token-based trace fitness measures the extent to which an event log can be successfully replayed by a Petri net. It tracks four types of tokens during the simulation of a trace:

* $c$ = Consumed tokens
* $p$ = Produced tokens
* $m$ = Missing tokens (tokens that had to be artificially created to force a transition to fire)
* $r$ = Remaining tokens (tokens left over in the net after the trace finishes executing)

The token fitness $f$ for an entire event log $L$ is calculated using the following formula:

$$f(L, N) = \frac{1}{2} \left( 1 - \frac{\sum_{\sigma \in L} L(\sigma) \cdot m(\sigma, N)}{\sum_{\sigma \in L} L(\sigma) \cdot c(\sigma, N)} \right) + \frac{1}{2} \left( 1 - \frac{\sum_{\sigma \in L} L(\sigma) \cdot r(\sigma, N)}{\sum_{\sigma \in L} L(\sigma) \cdot p(\sigma, N)} \right)$$

Where:

* $N$ represents the Petri net model.
* $\sigma$ represents a specific trace in the log.
* $L(\sigma)$ is the frequency (multiplicity) of that trace within the event log.

### Behavioral Precision

Behavioral precision measures how tightly the model encapsulates the behavior observed in the log. It penalizes the model if it frequently enables transitions that are never actually executed by the process.

For a log $L$ replayed on a net $N$, the precision $P_B$ is calculated step-by-step across all event execution points:

$$P_B(L, N) = \frac{\sum_{\sigma \in L} L(\sigma) \sum_{k=1}^{|\sigma|} |E_{fired}(\sigma_k)|}{\sum_{\sigma \in L} L(\sigma) \sum_{k=1}^{|\sigma|} |E_{enabled}(\sigma_k, N)|}$$

Where:
* $|\sigma|$ is the total length of the trace.
* $\sigma_k$ represents the $k$-th execution step in that trace.
* $E_{fired}(\sigma_k)$ is the set of transitions that actually fired at step $k$ (which is always $1$ for standard sequential logs).
* $E_{enabled}(\sigma_k, N)$ is the total set of transitions that were structurally unlocked and *capable* of firing at that exact state in the Petri net.

### Structural size and structural density (The E-C-N Metric)

The most direct way to calculate simplicity is by assessing the fundamental footprint of the graph structure. A model becomes less simple as the number of nodes (places + transitions) and edges (arcs) grows.

We compute this using two primary variables:

* *Cardinaliates*: Total number of Arcs ($A$), Places ($P$), and Transitions ($T$).
* *Structural Size Score*: 
$$\text{Size} = |P| + |T| + |A|$$

Alternatively, you can compute **Graph Density**, which measures how close the Petri net is to being fully interconnected (where lower density typically indicates a cleaner, more readable sequential flow):

$$\text{Density} = \frac{|A|}{|P| \times |T|}$$

### Cyclomatic complexity 

Originally designed for software engineering to count independent pathways through source code, **Cyclomatic Complexity** adapts perfectly to Petri nets to measure control-flow complexity. It identifies how many distinct structural pathways or loops exist in your model layout. For a directed graph, the formula is:

$$V(G) = |A| - (|P| + |T|) + 2 \times P_{components}$$

*(Where $P_{components}$ is the number of connected components, which is equal to `1` for a single unified Petri net).*

A low Cyclomatic Complexity (e.g., 1 to 5) means the model is highly sequential or has very straightforward choices. A high score means the model contains deeply nested loops or heavily intertwined conditional paths.

### Control-Flow Complexity (weighted coupling)

This metric assesses how difficult it is to trace tokens through the split and join points of the model. Every time a Petri net branches out into an XOR or an AND split, it adds cognitive load for the person reading it. To compute a basic proxy of Control-Flow Complexity (CFC), you look exclusively at the transitions ($T$) and count their degree of connection, where *Fan-out* is the number of output places a transition leads to, and *Fan-in* is the number of input places leading into a transition:

$$\text{CFC Score} = \sum_{t \in T} (\text{Fan-out}(t) - 1)^2$$

A pure sequence net where every transition connects exactly 1 place to 1 place will score a `0` (perfect structural simplicity).

> TO DO: missing genralization measures.

## References

- [1] van der Aalst, W. M. P. (2010). Process Discovery: Capturing the Invisible. IEEE Computational Intelligence Magazine, 5(1), 28-41.
- [2] Weijters, A. J. M. M., Van der Aalst, W. M. P., & Alves de Medeiros, A. K. (2006). Process mining with the heuristics miner-algorithm. Technische Universiteit Eindhoven, Department of Technology Management.
- [3] Leemans, S. J., Fahland, D., & Van Der Aalst, W. M. (2013). Discovering block-structured process models from event logs—a general framework. In Business Process Management: 11th International Conference, BPM 2013.
- [4] Van Der Aalst, W. M. P. (2016). Process Mining: Data Science in Action
- [5] Rozinat, A., & van der Aalst, W. M. P. (2008). Conformance checking of processes based on monitoring data. Information Systems, 33(1), 64-97.
- [6] Berti, A., & van der Aalst, W. M. P. (2020). A novel token-based replay technique to speed up conformance checking and process enhancement. Transactions on Petri Nets and Other Models of Concurrency XV, 2021.
- [7] McCabe, T. J. (1976). A complexity measure. IEEE Transactions on Software Engineering, (4), 308-320. 
- [8] Lassen, K. B., & van der Aalst, W. M. P. (2009). Complexity metrics for Workflow nets. Information and Software Technology, 51(3), 610-626. Control
