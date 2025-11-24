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

class InputProcessor:
    def __init__(self):
        pass

    @staticmethod
    def process_data(text_data, integer_inputs):
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
