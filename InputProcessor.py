from SearchInput import SearchInput
from helper_classes.Slot import Slot
from helper_classes.Lecture import Lecture

def check_header(line):
    if line == "Name:":
        return 1
    elif line == "Lecture slots:":
        return 2
    elif line == "Tutorial slots:":
        return 3
    elif line == "Lectures:":
        return 4
    elif line == "Tutorials:":
        return 5
    elif line == "Not compatible:":
        return 6
    elif line == "Unwanted:":
        return 7
    elif line == "Preferences:":
        return 8
    elif line == "Pair:":
        return 9
    elif line == "Partial assignments:":
        return 10
    else:
        return 0

def split_sections(text_data):
    lines = text_data.splitlines()

    current_section = 0

    name = ""
    lecture_slots = []
    tutorial_slots = []
    lectures = []
    tutorials = []
    not_compatible = []
    unwanted = []
    preferences = []
    pair = []
    partial_assignments = []

    for line in lines:
        if check_header(line) != 0:
            current_section = check_header(line)
        else:
            if line != "":
                if current_section == 1:
                    name = line
                elif current_section == 2:
                    lecture_slots.append(line)
                elif current_section == 3:
                    tutorial_slots.append(line)
                elif current_section == 4:
                    lectures.append(line)
                elif current_section == 5:
                    tutorials.append(line)
                elif current_section == 6:
                    not_compatible.append(line)
                elif current_section == 7:
                    unwanted.append(line)
                elif current_section == 8:
                    preferences.append(line)
                elif current_section == 9:
                    pair.append(line)
                elif current_section == 10:
                    partial_assignments.append(line)

    out = [name, lecture_slots, tutorial_slots, lectures, tutorials, not_compatible, unwanted, preferences, pair, partial_assignments]
    return out

def bool_string(text):
    if text == "true":
        return True
    elif text == "false":
        return False
    return None

def process_lecture_slots(lines):
    slots = []
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        slot = Slot(cleaned_data[0],cleaned_data[1],int(cleaned_data[2]),int(cleaned_data[3]),int(cleaned_data[4]),False)
        slots.append(slot)
    return slots

def process_tutorial_slots(lines):
    slots = []
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        slot = Slot(cleaned_data[0],cleaned_data[1],int(cleaned_data[2]),int(cleaned_data[3]),int(cleaned_data[4]),True)
        slots.append(slot)
    return slots

def process_lectures(lines):
    lectures = []
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        lec = Lecture(cleaned_data[0],bool_string(cleaned_data[1]))
        lectures.append(lec)
    return lectures

def process_tutorials(lines):
    tutorials = []
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        tut = Lecture(cleaned_data[0],bool_string(cleaned_data[1]))
        tutorials.append(tut)
    return tutorials

def process_not_compatible(lines):
    lst = set()
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        l = frozenset([cleaned_data[0],cleaned_data[1]])
        lst.add(l)
    return lst

def process_unwanted(lines):
    lst = set()
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        slot = cleaned_data[1] + ' ' + cleaned_data[2]
        l = frozenset([cleaned_data[0],slot])
        lst.add(l)
    return lst

def process_preferences(lines):
    lst = set()
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        slot = cleaned_data[0] + ' ' + cleaned_data[1]
        l = frozenset([cleaned_data[2],slot, int(cleaned_data[3])])
        lst.add(l)
    return lst

def process_pair(lines):
    lst = set()
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        l = frozenset([cleaned_data[0],cleaned_data[1]])
        lst.add(l)
    return lst

def process_partial_assignments(lines):
    lst = set()
    for line in lines:
        data = line.split(',')
        cleaned_data = [x.strip() for x in data]
        slot = cleaned_data[1] + ' ' + cleaned_data[2]
        l = frozenset([cleaned_data[0],slot])
        lst.add(l)
    return lst

class InputProcessor:
    def __init__(self):
        pass

    @staticmethod
    def process_data(text_data, integer_inputs):
        sections = split_sections(text_data)

        lecture_slots = process_lecture_slots(sections[1])
        tutorial_slots = process_tutorial_slots(sections[2])
        lectures = process_lectures(sections[3])
        tutorials = process_tutorials(sections[4])
        not_compatible = process_not_compatible(sections[5])
        unwanted = process_unwanted(sections[6])
        preferences = process_preferences(sections[7])
        pair = process_pair(sections[8])
        partial_assignments = process_partial_assignments(sections[9])

        out = SearchInput(
            sections[0],
            lecture_slots,
            tutorial_slots,
            lectures,
            tutorials,
            not_compatible,
            unwanted,
            preferences,
            pair,
            partial_assignments,
            integer_inputs[0],
            integer_inputs[1],
            integer_inputs[2],
            integer_inputs[3],
            integer_inputs[4],
            integer_inputs[5],
            integer_inputs[6],
            integer_inputs[7]
        )
        return out
