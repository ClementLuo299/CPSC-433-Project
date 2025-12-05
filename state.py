class State:
    def __init__(self, problem, assignments=None, slot_usage=None, assigned_500_slots=None):
        self.problem = problem
        self.assignments = assignments if assignments is not None else {}
        # slot_usage: slot -> {'LEC': count, 'TUT': count, 'LAB': count}
        self.slot_usage = slot_usage if slot_usage is not None else {}
        # assigned_500_slots: list of Slot objects occupied by 500-level courses
        self.assigned_500_slots = assigned_500_slots if assigned_500_slots is not None else []
        
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
            new_slot_usage[slot] = {'LEC': 0, 'TUT': 0, 'LAB': 0}
        else:
            new_slot_usage[slot] = new_slot_usage[slot].copy()
            
        if course.type == "LEC":
            new_slot_usage[slot]['LEC'] += 1
        elif course.type == "TUT":
            new_slot_usage[slot]['TUT'] += 1
        elif course.type == "LAB":
            new_slot_usage[slot]['LAB'] += 1
            
        new_assigned_500_slots = self.assigned_500_slots
        if course.is_500_level:
            new_assigned_500_slots = list(self.assigned_500_slots) # Copy list
            new_assigned_500_slots.append(slot)
            
        return State(self.problem, new_assignments, new_slot_usage, new_assigned_500_slots)

    def is_valid(self, course, slot):
        # 1. Max Capacity
        usage = self.slot_usage.get(slot, {'LEC': 0, 'TUT': 0, 'LAB': 0})
        if course.type == "LEC":
            if usage['LEC'] >= slot.lecture_max: 
                return False
        elif course.type == "TUT":
            if usage['TUT'] >= slot.lecture_max: # TUT uses lecture_max (col 2)
                return False
        elif course.type == "LAB":
            if usage['LAB'] >= slot.lecture_max: # LAB uses lecture_max (col 2)
                return False
            
        # 2. Active Learning (AL)
        # If this course requires AL but this slot doesn't have any AL capacity return false
        if course.al_required:
            al_capacity = slot.al_max
            if al_capacity == 0:
                return False
            elif al_capacity > 0:
                al_taken = 0

                # For all courses already in this slot, if it requires AL increment counter by 1
                # If counter > al_capacity return false
                for assigned_course, assigned_slot in self.assignments.items():
                    if assigned_slot == slot:
                        if assigned_course.al_required:
                            al_taken += 1
                            if al_taken >= al_capacity:
                                return False
        
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
        # Optimized check using adjacency list
        if course in self.problem.incompatible_map:
            for incompatible_course in self.problem.incompatible_map[course]:
                if incompatible_course in self.assignments:
                    assigned_slot = self.assignments[incompatible_course]
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
        # "All lectures with course number 5XX must be in non-overlapping time slots (pairwise incompatible)."
        if course.is_500_level and course.type == "LEC":
            # Check against all currently assigned 500-level LECTURES
            for assigned_course, assigned_slot in self.assignments.items():
                if assigned_course.is_500_level and assigned_course.type == "LEC":
                    if slot.overlaps(assigned_slot):
                        return False
        
        # 8. Evening Classes
        if course.is_evening:
            if slot.hour < 18:
                return False
                
        # 9. Tuesday 11:00-12:30 (No Lectures)
        if course.type == "LEC":
            if slot.day == "TU" and slot.hour == 11 and slot.minute == 0:
                return False
            
        if not self.check_special_constraints(course, slot):
            return False

        return True

    
# Special Constraints (CPSC 851/913)
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
        
        # If 351 exists in the PROBLEM (even if not assigned yet), 851 MUST be TU 18:00
        if course.number == 851 and course.dept == "CPSC":
             # Check existence of 351
             c351 = None
             for c in self.problem.lectures:
                 if c.dept == "CPSC" and c.number == 351:
                     c351 = c
                     break
             if c351:
                 if slot.id != "TU, 18:00":
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

        # If 413 exists in the PROBLEM, 913 MUST be TU 18:00
        if course.number == 913 and course.dept == "CPSC":
             c413 = None
             for c in self.problem.lectures:
                 if c.dept == "CPSC" and c.number == 413:
                     c413 = c
                     break
             if c413:
                 if slot.id != "TU, 18:00":
                     return False
                    
        if course.number == 413 and course.dept == "CPSC":
            c913 = None
            for c in self.problem.lectures:
                if c.dept == "CPSC" and c.number == 913:
                    c913 = c
                    break
            if not c913:
                return False
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
            total_usage = usage['LEC'] + usage['TUT'] + usage['LAB']
            if total_usage < slot.lecture_min:
                cost += (slot.lecture_min - total_usage) * w_minfilled
        return cost
