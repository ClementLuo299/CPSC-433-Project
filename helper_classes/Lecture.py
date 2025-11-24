class Lecture():
    def __init__(self, identifier, al):
        self.identifier = identifier
        self.al = al

    # get the subject and course number
    def get_course(self):
        parts = self.identifier.split(' ')
        return parts[0] + ' ' + parts[1]

    # get the lecture number
    def get_number(self):
        parts = self.identifier.split(' ')
        return parts[3]

    # get if AL is required
    def al_required(self):
        return self.al