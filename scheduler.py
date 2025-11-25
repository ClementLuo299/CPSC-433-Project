import sys
import argparse
import heapq
import copy
from collections import defaultdict

# ==========================================
# Data Structures
# ==========================================

class Course:
    def __init__(self, line):
        # Format: "CPSC 433 LEC 01" or "CPSC 433 LEC 01 TUT 01"
        parts = line.strip().split(',')
        self.id = parts[0].strip()
        self.al_required = False
        if len(parts) > 1:
            self.al_required = parts[1].strip().lower() == 'true'
        
        # Parse ID components
        id_parts = self.id.split()
        self.dept = id_parts[0]
        self.number = int(id_parts[1])
        self.type = "LEC" if "LEC" in id_parts and "TUT" not in id_parts and "LAB" not in id_parts else "TUT"
        
        # Extract section number
        # Example: CPSC 433 LEC 01 -> section 01
        # Example: CPSC 433 LEC 01 TUT 01 -> section 01 (of TUT)
        self.section = id_parts[-1]
        
        self.is_500_level = (self.number // 100 == 5)
        self.is_evening = self.section.startswith('9')
        
        # For linking Lecture and Tutorial (No Overlap constraint)
        # Parent lecture ID: "CPSC 433 LEC 01 TUT 01" -> "CPSC 433 LEC 01"
        self.parent_id = None
        if self.type == "TUT":
            # Find the index of "TUT" or "LAB"
            try:
                idx = id_parts.index("TUT")
            except ValueError:
                idx = id_parts.index("LAB")
            self.parent_id = " ".join(id_parts[:idx])

    def __repr__(self):
        return self.id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id
    
    def __lt__(self, other):
        return self.id < other.id

class Slot:
    def __init__(self, line, slot_type):
        # Format: "MO, 8:00, 3,2,1"
        parts = line.strip().split(',')
        self.day = parts[0].strip()
        self.time = parts[1].strip()
        self.id = f"{self.day}, {self.time}"
        self.slot_type = slot_type # "LEC" or "TUT"
        
        # Parse capacities
        # Assumption: LectureMax, LabMax, MinFilled
        self.lecture_max = int(parts[2])
        self.lab_max = int(parts[3])
        self.min_filled = int(parts[4])
        
        # Parse time for evening check
        time_parts = self.time.split(':')
        self.hour = int(time_parts[0])
        self.minute = int(time_parts[1])
        
        # Atomic Slots for Collision Detection
        # "Linked Slots" logic
        self.atomic_slots = set()
        if self.slot_type == "LEC":
            if self.day == "MO": # MWF
                self.atomic_slots.add(("MO", self.time))
                self.atomic_slots.add(("WE", self.time))
                self.atomic_slots.add(("FR", self.time))
            elif self.day == "TU": # TR
                self.atomic_slots.add(("TU", self.time))
                self.atomic_slots.add(("TH", self.time))
            else:
                # Fallback or other days
                self.atomic_slots.add((self.day, self.time))
        else: # TUT
            if self.day == "MO": # MW
                self.atomic_slots.add(("MO", self.time))
                self.atomic_slots.add(("WE", self.time))
            elif self.day == "TU": # TR
                self.atomic_slots.add(("TU", self.time))
                self.atomic_slots.add(("TH", self.time))
            elif self.day == "FR": # F
                self.atomic_slots.add(("FR", self.time))
            else:
                self.atomic_slots.add((self.day, self.time))

    def overlaps(self, other_slot):
        return not self.atomic_slots.isdisjoint(other_slot.atomic_slots)

    def __repr__(self):
        return self.id
    
    def __hash__(self):
        return hash((self.id, self.slot_type))
    
    def __eq__(self, other):
        return self.id == other.id and self.slot_type == other.slot_type

class ProblemInstance:
    def __init__(self):
        self.lectures = []
        self.tutorials = []
        self.lecture_slots = []
        self.tutorial_slots = []
        self.incompatible = set() # Set of frozenset({c1, c2})
        self.unwanted = defaultdict(list) # course -> list[slot_id]
        self.preferences = defaultdict(list) # course -> list[(slot_id, value)]
        self.pairs = [] # list[(c1, c2)]
        self.partial_assignments = {} # course -> slot_id
        
        # Lookups
        self.courses_by_id = {}
        self.slots_by_id = {} # (id, type) -> Slot

    def get_course(self, course_id):
        return self.courses_by_id.get(course_id)
    
    def get_slot(self, slot_id, slot_type):
        return self.slots_by_id.get((slot_id, slot_type))

    def precompute_valid_slots(self):
        self.valid_slots = {} # course -> list[slot]
        all_courses = self.lectures + self.tutorials
        for course in all_courses:
            valid = []
            possible = self.lecture_slots if course.type == "LEC" else self.tutorial_slots
            for slot in possible:
                # Check static constraints
                # 1. Unwanted
                if slot.id in self.unwanted[course]:
                    continue
                # 2. Evening
                if course.is_evening and slot.hour < 18:
                    continue
                # 3. Tuesday 11:00
                if course.type == "LEC" and slot.day == "TU" and slot.hour == 11 and slot.minute == 0:
                    continue
                # 4. AL (If we enforced it, check here)
                
                valid.append(slot)
            self.valid_slots[course] = valid

# ==========================================
# State Representation
# ==========================================

class State:
    def __init__(self, problem, assignments=None, slot_usage=None, assigned_500_slots=None):
        self.problem = problem
        self.assignments = assignments if assignments is not None else {}
        # slot_usage: slot -> {'LEC': count, 'TUT': count}
        self.slot_usage = slot_usage if slot_usage is not None else {}
        # assigned_500_slots: set of atomic slots occupied by 500-level courses
        self.assigned_500_slots = assigned_500_slots if assigned_500_slots is not None else set()
        
    def is_complete(self):
        return len(self.assignments) == (len(self.problem.lectures) + len(self.problem.tutorials))
    
    def get_unassigned_courses(self):
        all_courses = self.problem.lectures + self.problem.tutorials
        return [c for c in all_courses if c not in self.assignments]

    def assign(self, course, slot):
        # Create new state (lightweight copy)
        new_assignments = self.assignments.copy()
        new_assignments[course] = slot
        
        new_slot_usage = self.slot_usage.copy()
        if slot not in new_slot_usage:
            new_slot_usage[slot] = {'LEC': 0, 'TUT': 0}
        else:
            new_slot_usage[slot] = new_slot_usage[slot].copy()
            
        if course.type == "LEC":
            new_slot_usage[slot]['LEC'] += 1
        else:
            new_slot_usage[slot]['TUT'] += 1
            
        new_assigned_500_slots = self.assigned_500_slots
        if course.is_500_level:
            new_assigned_500_slots = self.assigned_500_slots.copy()
            new_assigned_500_slots.update(slot.atomic_slots)
            
        return State(self.problem, new_assignments, new_slot_usage, new_assigned_500_slots)

    def is_valid(self, course, slot):
        # 1. Max Capacity
        usage = self.slot_usage.get(slot, {'LEC': 0, 'TUT': 0})
        if course.type == "LEC":
            if usage['LEC'] >= slot.lecture_max: return False
        else:
            if usage['TUT'] >= slot.lab_max: return False
            
        # 2. Active Learning (AL)
        # Assumption: If AL required, LectureMax (or LabMax) must be > 0? 
        # Or maybe AL is not strictly enforced by capacity in this simplified input?
        # Prompt says: "If a course requires AL, the slot must have ALmax > 0."
        # Given input format `3,2,1`, we assume `3` is LectureMax. If `3 > 0`, it supports AL?
        # Let's assume standard slots support AL if they have capacity.
        
        # 3. No Overlap (Lecture vs its own Tutorial)
        if course.type == "TUT" and course.parent_id:
            parent = self.problem.get_course(course.parent_id)
            if parent and parent in self.assignments:
                parent_slot = self.assignments[parent]
                if slot.overlaps(parent_slot):
                    return False
        elif course.type == "LEC":
            # Check if any of its tutorials are already assigned
            # This requires reverse lookup or iterating assignments.
            # Optimization: Iterate assignments is O(N), acceptable for small N.
            for assigned_course, assigned_slot in self.assignments.items():
                if assigned_course.type == "TUT" and assigned_course.parent_id == course.id:
                    if slot.overlaps(assigned_slot):
                        return False

        # 4. Not Compatible
        for assigned_course, assigned_slot in self.assignments.items():
            if frozenset({course, assigned_course}) in self.problem.incompatible:
                if slot.overlaps(assigned_slot):
                    return False
        
        # 5. Unwanted
        if slot.id in self.problem.unwanted[course]:
            return False
            
        # 6. Partial Assignments (Handled by pre-assignment, but check for consistency)
        if course in self.problem.partial_assignments:
            required_slot_id = self.problem.partial_assignments[course]
            if slot.id != required_slot_id:
                return False
                
        # 7. 500-Level
        if course.is_500_level:
            if not slot.atomic_slots.isdisjoint(self.assigned_500_slots):
                return False
        
        # 8. Evening Classes
        if course.is_evening:
            if slot.hour < 18:
                return False
                
        # 9. Tuesday 11:00-12:30 (No Lectures)
        if course.type == "LEC":
            if slot.day == "TU" and slot.hour == 11 and slot.minute == 0:
                return False
                
        # 10. Special CPSC 851/913
        # "If CPSC 351 is scheduled, CPSC 851 must be TU 18:00 (and cannot overlap 351)."
        # This is a complex conditional constraint.
        # It implies we need to check if 351 is assigned.
        # Let's handle this by checking if `course` is 851 or 913, or if `course` is 351/413.
        # This is very specific. I'll implement a helper for this.
        if not self.check_special_constraints(course, slot):
            return False

        return True

    def check_special_constraints(self, course, slot):
        # CPSC 851 vs CPSC 351
        # CPSC 913 vs CPSC 413
        # If 351 is scheduled, 851 must be TU 18:00
        
        # Case 1: Assigning 851
        if course.number == 851 and course.dept == "CPSC":
            # Check if 351 is assigned
            c351 = None
            for c in self.problem.lectures:
                if c.dept == "CPSC" and c.number == 351:
                    c351 = c
                    break
            if c351 and c351 in self.assignments:
                # 351 is assigned, so 851 MUST be TU 18:00
                if slot.id != "TU, 18:00":
                    return False
                # And cannot overlap 351 (Implicitly handled by Not Compatible if defined, or we check here)
                if slot.overlaps(self.assignments[c351]):
                    return False
        
        # Case 2: Assigning 351
        if course.number == 351 and course.dept == "CPSC":
            # Check if 851 is assigned
            c851 = None
            for c in self.problem.lectures:
                if c.dept == "CPSC" and c.number == 851:
                    c851 = c
                    break
            if c851 and c851 in self.assignments:
                # 851 is assigned, so it MUST be TU 18:00.
                if self.assignments[c851].id != "TU, 18:00":
                    return False # Should have been caught earlier, but for safety
                if slot.overlaps(self.assignments[c851]):
                    return False

        # Same for 913/413
        if course.number == 913 and course.dept == "CPSC":
            c413 = None
            for c in self.problem.lectures:
                if c.dept == "CPSC" and c.number == 413:
                    c413 = c
                    break
            if c413 and c413 in self.assignments:
                if slot.id != "TU, 18:00":
                    return False
                if slot.overlaps(self.assignments[c413]):
                    return False
                    
        if course.number == 413 and course.dept == "CPSC":
            c913 = None
            for c in self.problem.lectures:
                if c.dept == "CPSC" and c.number == 913:
                    c913 = c
                    break
            if c913 and c913 in self.assignments:
                if self.assignments[c913].id != "TU, 18:00":
                    return False
                if slot.overlaps(self.assignments[c913]):
                    return False
                    
        return True

    def __lt__(self, other):
        # Tie-breaker for Priority Queue
        # Prefer states with MORE assignments (closer to goal)
        return len(self.assignments) > len(other.assignments)


    def calculate_cost(self, weights):
        w_minfilled, w_pref, w_pair, w_secdiff, pen_notpaired, pen_section = weights
        cost = 0
        
        # 1. MinFilled
        # "If slot usage < min, penalty = (min - usage) * weight"
        # We assume Wminfilled is the weight.
        # We ignore pen_lecturemin/pen_tutorialmin as per prompt formula.
        
        # 2. Preferences
        for course, slot in self.assignments.items():
            prefs = self.problem.preferences[course]
            for pref_slot_id, val in prefs:
                if slot.id != pref_slot_id:
                    cost += val * w_pref

        # 3. Pair
        # "If pair(A, B) and time(A) != time(B), add pen_notpaired."
        for c1, c2 in self.problem.pairs:
            if c1 in self.assignments and c2 in self.assignments:
                s1 = self.assignments[c1]
                s2 = self.assignments[c2]
                if not s1.overlaps(s2):
                    cost += pen_notpaired * w_pair
        
        # 4. SecDiff
        # "If two sections of the same course are in the same slot, add pen_section."
        assigned_list = list(self.assignments.items())
        for i in range(len(assigned_list)):
            c1, s1 = assigned_list[i]
            for j in range(i + 1, len(assigned_list)):
                c2, s2 = assigned_list[j]
                if c1.dept == c2.dept and c1.number == c2.number and c1.type == c2.type:
                    # Same course, different sections
                    if s1.overlaps(s2):
                        cost += pen_section * w_secdiff
                        
        return cost

    def calculate_minfilled_cost(self, w_minfilled):
        cost = 0
        for slot, usage in self.slot_usage.items():
            total_usage = usage['LEC'] + usage['TUT']
            if total_usage < slot.min_filled:
                cost += (slot.min_filled - total_usage) * w_minfilled
        return cost

# ==========================================
# Parser
# ==========================================

def parse_file(filename):
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    problem = ProblemInstance()
    
    mode = None
    for line in lines:
        if line.startswith("Name:"):
            mode = "Name"
            continue
        elif line.startswith("Lecture slots:"):
            mode = "Lecture slots"
            continue
        elif line.startswith("Tutorial slots:"):
            mode = "Tutorial slots"
            continue
        elif line.startswith("Lectures:"):
            mode = "Lectures"
            continue
        elif line.startswith("Tutorials:"):
            mode = "Tutorials"
            continue
        elif line.startswith("Not compatible:"):
            mode = "Not compatible"
            continue
        elif line.startswith("Unwanted:"):
            mode = "Unwanted"
            continue
        elif line.startswith("Preferences:"):
            mode = "Preferences"
            continue
        elif line.startswith("Pair:"):
            mode = "Pair"
            continue
        elif line.startswith("Partial assignments:"):
            mode = "Partial assignments"
            continue
            
        # Process data based on mode
        if mode == "Name":
            pass # Ignore name
        elif mode == "Lecture slots":
            problem.lecture_slots.append(Slot(line, "LEC"))
        elif mode == "Tutorial slots":
            problem.tutorial_slots.append(Slot(line, "TUT"))
        elif mode == "Lectures":
            c = Course(line)
            problem.lectures.append(c)
            problem.courses_by_id[c.id] = c
        elif mode == "Tutorials":
            c = Course(line)
            problem.tutorials.append(c)
            problem.courses_by_id[c.id] = c
        elif mode == "Not compatible":
            parts = line.split(',')
            id1 = parts[0].strip()
            id2 = parts[1].strip()
            c1 = problem.get_course(id1)
            c2 = problem.get_course(id2)
            if c1 and c2:
                problem.incompatible.add(frozenset({c1, c2}))
        elif mode == "Unwanted":
            parts = line.split(',')
            c_id = parts[0].strip()
            day = parts[1].strip()
            time = parts[2].strip()
            slot_id = f"{day}, {time}"
            c = problem.get_course(c_id)
            if c:
                problem.unwanted[c].append(slot_id)
        elif mode == "Preferences":
            parts = line.split(',')
            day = parts[0].strip()
            time = parts[1].strip()
            c_id = parts[2].strip()
            val = int(parts[3].strip())
            slot_id = f"{day}, {time}"
            c = problem.get_course(c_id)
            if c:
                problem.preferences[c].append((slot_id, val))
        elif mode == "Pair":
            parts = line.split(',')
            id1 = parts[0].strip()
            id2 = parts[1].strip()
            c1 = problem.get_course(id1)
            c2 = problem.get_course(id2)
            if c1 and c2:
                problem.pairs.append((c1, c2))
        elif mode == "Partial assignments":
            parts = line.split(',')
            c_id = parts[0].strip()
            day = parts[1].strip()
            time = parts[2].strip()
            slot_id = f"{day}, {time}"
            c = problem.get_course(c_id)
            if c:
                problem.partial_assignments[c] = slot_id

    # Populate slot lookups
    for s in problem.lecture_slots:
        problem.slots_by_id[(s.id, "LEC")] = s
    for s in problem.tutorial_slots:
        problem.slots_by_id[(s.id, "TUT")] = s
        
    return problem

# ==========================================
# Solver
# ==========================================

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


# ==========================================
# Main
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="University Course Scheduler")
    parser.add_argument("filename", help="Input file path")
    parser.add_argument("w_minfilled", type=float)
    parser.add_argument("w_pref", type=float)
    parser.add_argument("w_pair", type=float)
    parser.add_argument("w_secdiff", type=float)
    parser.add_argument("pen_lecturemin", type=float, help="Unused in standard spec but required by args")
    parser.add_argument("pen_tutorialmin", type=float, help="Unused")
    parser.add_argument("pen_notpaired", type=float)
    parser.add_argument("pen_section", type=float)
    
    args = parser.parse_args()
    
    problem = parse_file(args.filename)
    
    weights = (args.w_minfilled, args.w_pref, args.w_pair, args.w_secdiff, args.pen_notpaired, args.pen_section)
    
    solution, cost = solve(problem, weights)
    
    if solution:
        print(f"Eval-value: {int(cost)}")
        # Sort assignments: Alphabetical by Course ID
        sorted_assignments = sorted(solution.assignments.items(), key=lambda x: x[0].id)
        for course, slot in sorted_assignments:
            print(f"{course.id} : {slot.id}")
    else:
        print("No solution found.")

if __name__ == "__main__":
    main()


