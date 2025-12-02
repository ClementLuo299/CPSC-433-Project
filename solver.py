import heapq
from collections import defaultdict
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
        current_usage = state.slot_usage.get(slot, {'LEC': 0, 'TUT': 0})
        total_current = current_usage['LEC'] + current_usage['TUT']
        max_possible = total_current + potential_additions[slot]
        
        if max_possible < slot.min_filled:
            h += (slot.min_filled - max_possible) * w_minfilled

    # 2. Preference Heuristic
    # Sum of min preference penalty for each unassigned course
    for course in unassigned:
        min_pref_cost = float('inf')
        
        # If course has no preferences, min cost is 0
        if course not in state.problem.preferences:
            min_pref_cost = 0
        else:
            # Check all valid slots
            # If a valid slot is NOT in preferences, cost is 0?
            # Wait, how are preferences defined?
            # "If assigned slot != preferred slot, add specific preference penalty."
            # This usually implies:
            # List of (Slot, Penalty).
            # If assigned to Slot S, and S is in list, we pay Penalty?
            # No, usually "Preference: I want A (value 10)".
            # If I get A, cost 0. If I get B, cost 10?
            # The prompt says: "Preferences: If assigned slot != preferred slot, add specific preference penalty."
            # Input: `MO, 10:00, CPSC 231 LEC 01, 7`
            # This means: "Preferred is MO 10:00. Penalty for NOT getting it is 7."
            # So if I assign MO 10:00, cost 0.
            # If I assign anything else, cost 7.
            # What if multiple preferences?
            # "MO 10:00, 7", "TU 11:00, 3".
            # If MO 10:00 -> Miss TU 11:00 (3). Total 3.
            # If TU 11:00 -> Miss MO 10:00 (7). Total 7.
            # If WE 9:00 -> Miss both (10). Total 10.
            
            # So for a course, `base_penalty` = sum of all preference values.
            # If assigned to `s`, `reduction` = sum of values for preferences satisfied by `s`.
            # `cost` = `base_penalty` - `reduction`.
            # We want min cost.
            # So we want max reduction.
            
            # Pre-calculate base_penalty for the course?
            pass

        # Let's implement this logic correctly.
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

def find_initial_solution(state, weights, depth=0):
    # Greedy DFS to find ONE solution quickly
    if state.is_complete():
        return state, state.calculate_cost(weights) + state.calculate_minfilled_cost(weights[0])
    
    # MRV
    unassigned = state.get_unassigned_courses()
    # Simple MRV
    best_var = None
    min_valid = float('inf')
    
    # Optimization: Just pick one with fewest slots to fail fast
    candidates = []
    for course in unassigned:
        valid_slots = []
        for slot in state.problem.valid_slots[course]:
            if state.is_valid(course, slot):
                valid_slots.append(slot)
        if len(valid_slots) < min_valid:
            min_valid = len(valid_slots)
            best_var = course
            candidates = [(course, valid_slots)]
        elif len(valid_slots) == min_valid:
            candidates.append((course, valid_slots))
            
    # Tie break with degree?
    # Just pick first for speed
    if not candidates:
        return None, float('inf')
        
    # Sort candidates by degree?
    best_var, valid_slots = candidates[0]
    
    # LCV
    # Sort slots by cost
    scored_slots = []
    for slot in valid_slots:
        next_state = state.assign(best_var, slot)
        cost = next_state.calculate_cost(weights)
        scored_slots.append((cost, slot))
    scored_slots.sort(key=lambda x: x[0])
    
    for _, slot in scored_slots:
        next_state = state.assign(best_var, slot)
        sol, cost = find_initial_solution(next_state, weights, depth+1)
        if sol:
            return sol, cost
            
    return None, float('inf')

def solve(problem, weights):
    # Weights: Wminfilled, Wpref, Wpair, Wsecdiff, pen_notpaired, pen_section
    
    # Precompute valid slots
    problem.precompute_valid_slots()
    
    # Initial State
    initial_state = State(problem)
    
    # Apply Partial Assignments first (Hard Constraint)
    for course, slot_id in problem.partial_assignments.items():
        slot_type = course.type
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
    best_solution, best_cost = find_initial_solution(initial_state, weights)
    
    # 2. Branch-and-Bound Search (A*)
    pq = []
    start_g = initial_state.calculate_cost(weights)
    start_h = calculate_heuristic(initial_state, weights)
    heapq.heappush(pq, (start_g + start_h, initial_state))
    
    nodes_expanded = 0
    
    while pq:
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
