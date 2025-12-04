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
        
        if max_possible < slot.min_filled:
            h += (slot.min_filled - max_possible) * w_minfilled

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

def find_initial_solution(state, weights, depth=0, nodes_visited=None, randomize=False):
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
    if randomize:
        best_var, valid_slots = random.choice(candidates)
    else:
        best_var, valid_slots = candidates[0]
    
    # LCV
    # Sort slots by cost
    scored_slots = []
    for slot in valid_slots:
        next_state = state.assign(best_var, slot)
        cost = next_state.calculate_cost(weights)
        scored_slots.append((cost, slot))
    
    if randomize:
        # Add some noise to sorting or just shuffle top K?
        # Let's just shuffle equivalent costs or small noise
        random.shuffle(scored_slots) # Full shuffle for exploration
        scored_slots.sort(key=lambda x: x[0] + random.random() * 0.1) # Slight noise to break ties randomly
    else:
        scored_slots.sort(key=lambda x: x[0])
    
    for _, slot in scored_slots:
        next_state = state.assign(best_var, slot)
        sol, cost = find_initial_solution(next_state, weights, depth+1, nodes_visited, randomize)
        if sol:
            return sol, cost
            
    return None, float('inf')

# def try_one_greedy_build(initial_state, problem, max_steps=100000):
#     """
#     How about we just try to build ONE complete schedule greedily from initial_state.

#     - Respects all HARD constraints via state.is_valid.
#     - Ignores SOFT constraints while constructing.
#     """
#     state = initial_state
#     steps = 0

#     while not state.is_complete():
#         steps += 1
#         if steps > max_steps:
#             # Safety guard so we don't loop forever in some weird situation
#             print ("Guard time")
#             return None, False

#         unassigned = state.get_unassigned_courses()

#         # Choose next course (variable)

#         # Lectures are less flexible. lectures first, then tutorials/labs
#         lectures = [c for c in unassigned if c.type == "LEC"]
#         others   = [c for c in unassigned if c.type != "LEC"]

#         candidate_set = lectures if lectures else others

#         best_courses = []      # list of courses with minimal valid-slot count
#         best_valid_map = {}    # course -> its valid slot list
#         min_valid = float('inf')

#         for course in candidate_set:
#             valid_slots = [
#                 slot for slot in problem.valid_slots[course]
#                 if state.is_valid(course, slot)
#             ]

#             if not valid_slots:
#                 # This course cannot go anywhere in this attempt,
#                 # but maybe another course still can.
#                 # We don't immediately fail here; we let MRV pick someone else.
#                 continue

#             count = len(valid_slots)

#             if count < min_valid:
#                 min_valid = count
#                 best_courses = [course]
#                 best_valid_map[course] = valid_slots
#             elif count == min_valid:
#                 best_courses.append(course)
#                 best_valid_map[course] = valid_slots

#         # If NO course had any valid slots then this attempt is doomed
#         if not best_courses:
#             total_courses = len(state.problem.lectures) + len(state.problem.tutorials)
#             unassigned = state.get_unassigned_courses()
#             assigned = total_courses - len(unassigned)
#             print(f"    Attempt failed after assigning {assigned}/{total_courses} courses.")

#             # Choose one representative stuck course to inspect
#             stuck_course = unassigned[0]
#             print(f"    Inspecting stuck course: {stuck_course.id}")

#             # Static valid slots for this course
#             static_slots = state.problem.valid_slots[stuck_course]
#             print(f"      Static valid slots count: {len(static_slots)}")
#             for slot in static_slots:
#                 ok = state.is_valid(stuck_course, slot)
#                 print(f"        Slot {slot.id}: is_valid = {ok}")

#             return None, False


#         # ie-breaking for course choice ---

#         if len(best_courses) == 1:
#             chosen_course = best_courses[0]
#         else:
#             # All have same minimal number of valid slots.
#             # Randomly choose among these equally constrained courses.
#             chosen_course = random.choice(best_courses)

#         candidate_slots = best_valid_map[chosen_course]

#         # Choose a slot for this course ---

#         if len(candidate_slots) == 1:
#             chosen_slot = candidate_slots[0]
#         else:
#             # Simple strategy: randomly pick among valid slots.
#             chosen_slot = random.choice(candidate_slots)

#         # Assign and continue
#         state = state.assign(chosen_course, chosen_slot)

#     # If we exit the loop, all courses are assigned and hard constraints are satisfied.
#     return state, True

# def build_initial_solution_greedy(initial_state, problem, weights, max_restarts=50):
#     """
#     Try multiple greedy constructions with different tie-breaks to find
#     ONE complete, only hard-valid schedule.
#     """
#     best_state = None
#     best_cost = float('inf')

#     for r in range(max_restarts):
#         print(f"  Greedy restart {r+1}/{max_restarts}...")
#         state, success = try_one_greedy_build(initial_state, problem)

#         if not success or state is None:
#             continue

#         # We found a complete schedule; compute its Eval cost once
#         total_cost = state.calculate_cost(weights) + state.calculate_minfilled_cost(weights[0])

#         print(f"    → Found complete schedule with cost {total_cost}")

#         if total_cost < best_cost:
#             best_cost = total_cost
#             best_state = state

#             # We could keep looking for an even better one,
#             # but for our purposes, the first success is already good enough.
#             # If you want, you can break here.
#             break

#     if best_state is None:
#         return None, float('inf')
#     return best_state, best_cost



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
