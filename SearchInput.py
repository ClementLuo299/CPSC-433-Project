class SearchInput:
    def __init__(self,
                 name,
                 lecture_slots,
                 tutorial_slots,
                 lectures,
                 tutorials,
                 not_compatible,
                 unwanted,
                 preferences,
                 pair,
                 partial_assignments,
                 weight_minfilled,
                 weight_pref,
                 weight_pair,
                 weight_secdiff,
                 pen_lecturemin,
                 pen_tutorialmin,
                 pen_notpaired,
                 pen_section
                 ):
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
        self.weight_minfilled = weight_minfilled
        self.weight_pref = weight_pref
        self.weight_pair = weight_pair
        self.weight_secdiff = weight_secdiff
        self.pen_lecturemin = pen_lecturemin
        self.pen_tutorialmin = pen_tutorialmin
        self.pen_notpaired = pen_notpaired
        self.pen_section = pen_section