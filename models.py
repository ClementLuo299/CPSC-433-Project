from collections import defaultdict

#Dictionary containing bit mappings for slots
slot_index = {}

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
        self.type = "LEC"
        if "TUT" in id_parts:
            self.type = "TUT"
        elif "LAB" in id_parts:
            self.type = "LAB"
        
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
        # "Linked Slots" logic using bitmask
        self.mask = 0
        if self.slot_type == "LEC":
            if self.day == "MO": # MWF
                slot_list = [("MO", self.time), ("WE", self.time), ("FR", self.time)]
            elif self.day == "TU": # TR
                slot_list = [("TU", self.time), ("TH", self.time)]
            else:
                # Fallback or other days
                slot_list = [(self.day, self.time)]
        else: # TUT
            if self.day == "MO": # MW
                slot_list = [("MO", self.time), ("WE", self.time)]
            elif self.day == "TU": # TR
                slot_list = [("TU", self.time), ("TH", self.time)]
            elif self.day == "FR": # F
                slot_list = [("FR", self.time)]
            else:
                slot_list = [(self.day, self.time)]

        # Build atomic slots set and mask
        for dt in slot_list:
            # Assign bit to atomic slot if new
            if dt not in slot_index:
                slot_index[dt] = len(slot_index)

            bit = slot_index[dt]
            self.mask |= (1 << bit)

    def overlaps(self, other_slot):
        return (self.mask & other_slot.mask) != 0

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
        self.unwanted = defaultdict(set) # course -> list[slot_id]
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
