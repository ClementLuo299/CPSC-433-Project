import heapq
import random
from collections import defaultdict
import time
from state import State

def calculate_heuristic(state, weights):
    w_minfilled, w_pref, _, _, _, _ = weights
    h = 0
    
    # 1. MinFilled Heuristic (Unavoidable penalty)
    # For each slot, max possible usage = current + count(unassigned that CAN go here)
    # If max < min, add penalty.
    
    # Optimization: Pre-calculate "unassigned that can go to s" count?
    # Or just iterate.
    
    unassigned = state.get_unassigned_courses()
    
    # Count potential additions per slot
    # slot -> count
    potential_additions = defaultdict(int)
    
    for course in unassigned:
        # Use precomputed valid slots (Static validity)
        # This is a relaxation (ignores dynamic constraints), so it overestimates potential usage,
        # which underestimates penalty (Admissible).
        for slot in state.problem.valid_slots[course]:
            potential_additions[slot] += 1
            
    # Check all slots
    all_slots = state.problem.lecture_slots + state.problem.tutorial_slots
    for slot in all_slots:
        current_usage = state.slot_usage.get(slot, {'LEC': 0, 'TUT': 0, 'LAB': 0})
        total_current = current_usage['LEC'] + current_usage['TUT'] + current_usage['LAB']
        max_possible = total_current + potential_additions[slot]
        
        if max_possible < slot.lecture_min:
            h += (slot.lecture_min - max_possible) * w_minfilled

    # 2. Preference Heuristic
    # Sum of min preference penalty for each unassigned course
    for course in unassigned:
        min_pref_cost = float('inf')
        
        # If course has no preferences, min cost is 0
        if course not in state.problem.preferences:
            min_pref_cost = 0
        
        prefs = state.problem.preferences.get(course, [])
        if not prefs:
            continue
            
        base_penalty = sum(p[1] for p in prefs)
        max_reduction = 0
        
        for slot in state.problem.valid_slots[course]:
            # Calculate reduction if assigned to slot
            reduction = 0
            for p_slot_id, p_val in prefs:
                if slot.id == p_slot_id:
                    reduction += p_val
            if reduction > max_reduction:
                max_reduction = reduction
        
        min_cost = base_penalty - max_reduction
        h += min_cost * w_pref

    return h

# Note that the attempts parameter is different from the number of restarts in the solve function
# The attempts parameter is the number of attempts that we will conduct regardless of whether we found a solution or not
def find_initial_solution(state, weights, depth=0, nodes_visited=None, randomize=True, attempts=3):

    #This section only runs if we want to try for multiple attempts to find initial solution
    if depth == 0 and attempts > 1:
        best_sol = None
        best_cost = float('inf')

        # Run our search for each attempt
        for i in range(attempts):
            nodes = [0]
            sol, cost = find_initial_solution(state, weights, 0, nodes, randomize=randomize, attempts=1)
            if sol is not None and cost < best_cost:
                best_sol = sol
                best_cost = cost

        return best_sol, best_cost

    if nodes_visited is None:
        nodes_visited = [0]
    
    nodes_visited[0] += 1
    if nodes_visited[0] > 5000: # Increased limit to 5000 nodes
        return None, float('inf')

    # Greedy DFS to find ONE solution quickly
    if state.is_complete():
        return state, state.calculate_cost(weights) + state.calculate_minfilled_cost(weights[0])
    
    # MRV
    unassigned = state.get_unassigned_courses()
    # Simple MRV
    best_var = None
    min_valid = float('inf')
    
    # Optimization: Just pick one with the fewest slots to fail fast
    candidates = []
    for course in unassigned:
        valid_slots = []
        for slot in state.problem.valid_slots[course]:
            if state.is_valid(course, slot):
                valid_slots.append(slot)

        if len(valid_slots) == 0:
            return None, float('inf')

        if len(valid_slots) < min_valid:
            min_valid = len(valid_slots)
            candidates = [(course, valid_slots)]
        elif len(valid_slots) == min_valid:
            candidates.append((course, valid_slots))
            
    # Tie-break with degree?
    # Just pick first for speed
    if not candidates:
        return None, float('inf')
        
    # Sort candidates by degree?
    if randomize:
        best_var, valid_slots = random.choice(candidates)
    else:
        best_var, valid_slots = candidates[0]
    
    # LCV
    # Try just assigning a constant score for each slot since the search is slow
    scored_slots = [(0, slot) for slot in valid_slots]

    # Shuffle valid slots
    if randomize:
        random.shuffle(scored_slots)

    # Original code
    # Sort slots by cost
    """
    scored_slots = []
    for slot in valid_slots:
        next_state = state.assign(best_var, slot)
        cost = next_state.calculate_cost(weights)
        scored_slots.append((cost, slot))
    """
    
    if randomize:
        # Add some noise to sorting or just shuffle top K?
        # Let's just shuffle equivalent costs or small noise
        random.shuffle(scored_slots) # Full shuffle for exploration
        scored_slots.sort(key=lambda x: x[0] + random.random() * 0.1) # Slight noise to break ties randomly
    else:
        scored_slots.sort(key=lambda x: x[0])
    
    for _, slot in scored_slots:
        # Make temporary assignment
        temp = state.assign_inplace(best_var, slot)

        # Check for dead branches (where there are no valid slots)
        dead = False
        for crs in state.get_unassigned_courses():
            has_valid = False
            for sl in state.problem.valid_slots[crs]:
                if state.is_valid(crs, sl):
                    has_valid = True
                    break
            if not has_valid:
                dead = True
                break

        if dead:
            state.unassign_inplace(temp)
            continue

        sol, cost = find_initial_solution(state, weights, depth+1, nodes_visited, randomize)

        state.unassign_inplace(temp)

        if sol is not None:
            return sol, cost
            
    return None, float('inf')




def solve(problem, weights):
    # Weights: Wminfilled, Wpref, Wpair, Wsecdiff, pen_notpaired, pen_section
    
    # Precompute valid slots
    print("Precomputing valid slots...")
    problem.precompute_valid_slots()
    
    # Fail-Fast: Check for courses with NO valid slots
    for course, slots in problem.valid_slots.items():
        if not slots:
            print(f"CRITICAL ERROR: Course {course.id} has NO valid slots after precomputation!")
            print(f"  Unwanted: {problem.unwanted[course]}")
            print(f"  Evening: {course.is_evening}")
            return None, float('inf')
    
    # Initial State
    initial_state = State(problem)
    
    # Apply Partial Assignments first (Hard Constraint)
    for course, slot_id in problem.partial_assignments.items():
        slot_type = "LEC" if course.type == "LEC" else "TUT"
        slot = problem.get_slot(slot_id, slot_type)
        if not slot:
            print(f"Error: Partial assignment slot {slot_id} not found for {course.id}")
            return None
        if not initial_state.is_valid(course, slot):
            print(f"Error: Partial assignment {course.id} to {slot_id} is invalid")
            return None
        initial_state = initial_state.assign(course, slot)

    # 1. Find Initial Solution (Greedy DFS) to set bound
    # This helps prune the search space massively
    print("Finding initial solution (Greedy DFS)...")
    best_solution, best_cost = find_initial_solution(initial_state, weights)
    
    if best_solution:
        print(f"Initial solution found with cost: {best_cost}")
    else:
        print("No initial solution found with greedy DFS. Trying randomized restarts...")
        # Try randomized restarts
        for i in range(20): # Increased to 20 restarts
            print(f"Restart {i+1}/20...")
            sol, cost = find_initial_solution(initial_state, weights, nodes_visited=[0], randomize=True)
            if sol:
                best_solution = sol
                best_cost = cost
                print(f"Initial solution found in restart {i+1} with cost: {best_cost}")
                break
        
        if not best_solution:
            print("No initial solution found after restarts. Starting exhaustive search (this may be slow).")

    # 1. Find Initial Solution (Greedy + Restarts) to set bound
    # print("Finding initial solution (Greedy + Restarts)...")
    # best_solution, best_cost = build_initial_solution_greedy(initial_state, problem, weights)

    # if best_solution is not None:
    #     print(f"Initial solution found with cost: {best_cost}")
    # else:
    #     print("No initial solution found with greedy restarts. Proceeding without initial bound.")
    #     best_cost = float('inf')

    
    # 2. Branch-and-Bound Search (A*)
    print("Starting Branch-and-Bound search...")
    pq = []
    start_g = initial_state.calculate_cost(weights)
    start_h = calculate_heuristic(initial_state, weights)
    heapq.heappush(pq, (start_g + start_h, initial_state))
    
    nodes_expanded = 0
    
    start_time = time.time()
    timeout_seconds = 300 # 5 minutes timeout
    
    while pq:
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            print(f"Timeout reached ({timeout_seconds}s). Returning best solution found so far.")
            break
            
        f, state = heapq.heappop(pq)
        
        # Pruning
        if f >= best_cost:
            continue
            
        if state.is_complete():
            # Calculate FINAL cost including MinFilled
            final_cost = state.calculate_cost(weights) + state.calculate_minfilled_cost(weights[0])
            if final_cost < best_cost:
                best_cost = final_cost
                best_solution = state
            continue
            
        nodes_expanded += 1
        if nodes_expanded % 1000 == 0:
            print(f"Nodes expanded: {nodes_expanded}, PQ size: {len(pq)}, Current Best Cost: {best_cost}")
        
        # MRV: Select unassigned variable
        unassigned = state.get_unassigned_courses()
        
        best_var = None
        best_valid_slots = []
        min_valid_count = float('inf')
        max_degree = -1
        
        for course in unassigned:
            # Find valid slots
            # Use precomputed static slots to filter first?
            # Then check dynamic constraints.
            valid_slots = []
            possible_slots = problem.valid_slots[course] # Optimization
            
            for slot in possible_slots:
                if state.is_valid(course, slot):
                    valid_slots.append(slot)
            
            count = len(valid_slots)
            
            # Degree Heuristic
            degree = 0
            for s in problem.incompatible:
                if course in s: degree += 1
            for p in problem.pairs:
                if course in p: degree += 1
            
            if count < min_valid_count:
                min_valid_count = count
                best_var = course
                best_valid_slots = valid_slots
                max_degree = degree
            elif count == min_valid_count:
                if degree > max_degree:
                    best_var = course
                    best_valid_slots = valid_slots
                    max_degree = degree
        
        if best_var is None:
            continue
            
        if min_valid_count == 0:
            continue
            
        # Value Ordering: LCV
        scored_slots = []
        for slot in best_valid_slots:
            next_state = state.assign(best_var, slot)
            g = next_state.calculate_cost(weights)
            h = calculate_heuristic(next_state, weights)
            f_new = g + h
            scored_slots.append((f_new, next_state))
            
        scored_slots.sort(key=lambda x: x[0])
        
        for f_new, next_state in scored_slots:
            if f_new < best_cost:
                heapq.heappush(pq, (f_new, next_state))

    return best_solution, best_cost
