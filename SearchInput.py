class SearchInput:
    def __init__(self, name, lecture_slots, tutorial_slots, lectures, tutorials, not_compatible, unwanted, preferences,pair,partial_assignments):
        self.name = name
        self.lecture_slots = lecture_slots
        self.tutorial_slots = tutorial_slots
        self.lectures = lectures
        self.tutorials = tutorials
        self.not_compatible = not_compatible
        self.unwanted = unwanted
        self.preferences = preferences
        self.pair = pair
        self.partial_assignments = partial_assignments