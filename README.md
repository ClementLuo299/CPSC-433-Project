

## Algorithm Details

### 1. Search Strategy
- **Architecture**: And-Tree Search.
- **Strategy**: Best-First Search using a Priority Queue.
- **State Representation**: Each node in the tree represents a partial schedule.
- **Cost Function**: $f(n) = g(n) + h(n)$
    - $g(n)$: Actual penalty cost of the current partial assignment (Preferences, Pairs, Section Differences).
    - $h(n)$: Admissible heuristic estimating the remaining cost (MinFilled, Future Preferences).

### 2. Heuristics & Optimization
- **Branch-and-Bound**: The search maintains a global `best_solution_cost`. Any branch with $f(n) \ge best\_solution\_cost$ is pruned immediately.
- **Initialization**: A greedy Depth-First Search (DFS) runs first to find a quick initial solution. This establishes a tight bound for the main search, significantly improving performance.
- **Variable Ordering (MRV)**: The algorithm selects the course with the **Minimum Remaining Values** (fewest valid slots) to assign next. This implements the "fail-fast" principle.
- **Value Ordering (LCV)**: Slots are tried in order of **Least Constraining Value** (lowest immediate cost increase).

### 3. Constraints Handled
- **Hard Constraints** (Must be satisfied):
    - **Max Capacity**: Slot capacities for lectures and labs.
    - **No Overlap**: A lecture and its tutorials cannot overlap.
    - **Not Compatible**: Specific courses cannot overlap.
    - **Unwanted**: Courses restricted from specific slots.
    - **Partial Assignments**: Pre-assigned courses.
    - **500-Level**: No overlap between 500-level courses.
    - **Evening Classes**: Sections 9x must be at 18:00 or later.
    - **Tuesday 11:00**: No lectures during the department meeting.
    - **Linked Slots**: 
        - MWF Lectures: MO implies WE and FR.
        - TR Lectures: TU implies TH.
        - MW Tutorials: MO implies WE.
        - TR Tutorials: TU implies TH.
    - **Special Rules**: CPSC 851/913 constraints relative to 351/413.

- **Soft Constraints** (Minimized):
    - **MinFilled**: Penalizes slots used below minimum capacity.
    - **Preferences**: Penalizes assignments differing from instructor preferences.
    - **Pair**: Penalizes paired courses not scheduled at the same time.
    - **SecDiff**: Penalizes different sections of the same course scheduled at the same time.

## Setup and Usage

### Requirements
- Python 3.x
- Standard libraries only (no `pip install` needed).

### Running the Scheduler
The program is a single file `scheduler.py`. Run it from the command line with the input file and weights.

**Command Format:**
```bash
python3 scheduler.py <input_file> <Wminfilled> <Wpref> <Wpair> <Wsecdiff> <pen_lecturemin> <pen_tutorialmin> <pen_notpaired> <pen_section>
```

**Arguments:**
- `input_file`: Path to the input text file.
- `Wminfilled`: Weight for MinFilled penalty.
- `Wpref`: Weight for Preference penalty.
- `Wpair`: Weight for Pair penalty.
- `Wsecdiff`: Weight for Section Difference penalty.
- `pen_...`: Specific penalty values (used in calculation).

### Example
To run with the provided `input.txt` and default weights (e.g., all 1):

```bash
python3 scheduler.py input.txt 1 1 1 1 1 1 1 1
```

### Output Format
The program outputs the evaluation value (total penalty) and the list of assignments sorted alphabetically.

```text
Eval-value: 14
CPSC 231 LEC 01 : MO, 10:00
CPSC 231 LEC 01 TUT 01 : MO, 9:00
...
```
