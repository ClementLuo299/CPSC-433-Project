from models import Course, Slot, ProblemInstance

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
