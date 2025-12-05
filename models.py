from collections import defaultdict

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
        if len(id_parts) >= 4:
            self.dept = id_parts[0]
            try:
                self.number = int(id_parts[1])
            except ValueError:
                self.number = 0 # Default if not integer
            self.type = "LEC"
            if "TUT" in id_parts:
                self.type = "TUT"
            elif "LAB" in id_parts:
                self.type = "LAB"
            self.section = id_parts[-1]
        else:
            # Fallback for non-standard IDs (e.g. "L1")
            self.dept = "TEST"
            self.number = 0
            self.type = "LEC" # Default to LEC
            self.section = "01"
            # Try to guess type if "TUT" or "LAB" is in the string
            if "TUT" in self.id:
                self.type = "TUT"
            elif "LAB" in self.id:
                self.type = "LAB"
        
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
        # self.lecture_max = int(parts[2])
        # self.lab_max = int(parts[3])
        # self.min_filled = int(parts[4])

        # Parse capacities
        # Format: Day, Time, Max, Min, AL_Max
        # Example: MO, 8:00, 2, 0, 0
        try:
            self.lecture_max = int(parts[2])
            self.lecture_min = int(parts[3])
            # Check if AL_Max exists (it might be missing in some inputs)
            if len(parts) > 4:
                self.al_max = int(parts[4])
            else:
                self.al_max = 0 # Default to 0 if not specified
        except (IndexError, ValueError):
             # Fallback or error logging
             self.lecture_max = 0
             self.lecture_min = 0
             self.al_max = 0
        
        # Parse time for evening check
        time_parts = self.time.split(':')
        self.hour = int(time_parts[0])
        self.minute = int(time_parts[1])
        self.start_min = self.hour * 60 + self.minute
        
        # Determine Duration
        # Standard UofC: MWF = 60 mins (50+10), TR = 90 mins (75+15)
        # We assume this applies to ALL slots based on Day.
        if self.day in ["TU", "TH"]:
            self.duration = 90
        else:
            self.duration = 60
            
        self.end_min = self.start_min + self.duration
        
        # Atomic Slots for Collision Detection
        # Store (Day, Start, End)
        self.atomic_slots = set()
        days = []
        if self.slot_type == "LEC":
            if self.day == "MO": # MWF
                days = ["MO", "WE", "FR"]
            elif self.day == "TU": # TR
                days = ["TU", "TH"]
            else:
                days = [self.day]
        else: # TUT
            if self.day == "MO": # MW
                days = ["MO", "WE"]
            elif self.day == "TU": # TR
                days = ["TU", "TH"]
            else:
                days = [self.day]
                
        for d in days:
            self.atomic_slots.add((d, self.start_min, self.end_min))

    def overlaps(self, other_slot):
        # Check intersection of atomic slots
        # Two slots overlap if they share a Day AND their time ranges overlap
        for d1, s1, e1 in self.atomic_slots:
            for d2, s2, e2 in other_slot.atomic_slots:
                if d1 == d2:
                    # Check time overlap: max(start1, start2) < min(end1, end2)
                    if max(s1, s2) < min(e1, e2):
                        return True
        return False

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
        self.incompatible_map = defaultdict(set) # course -> set[course]
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
                # 3. Tuesday 11:00 - REMOVED (Input file allows it)
                # if course.type == "LEC" and slot.day == "TU" and slot.hour == 11 and slot.minute == 0:
                #     continue
                # 4. AL (If we enforced it, check here)
                
                valid.append(slot)
            self.valid_slots[course] = valid
