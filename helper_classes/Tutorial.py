from helper_classes.Lecture import Lecture

class Tutorial(Lecture):

    # get the tutorial number
    def get_number(self):
        parts = self.identifier.split(' ')
        return parts[5]

    # returns True if the tutorial is a lab, False otherwise
    def is_lab(self):
        parts = self.identifier.split(' ')
        if parts[4] == 'LAB':
            return True
        else:
            return False

    # access the associated lecture
    def get_associated_lecture(self):
        parts = self.identifier.split(' ')
        lec_identifier = parts[0] + ' ' + parts[1] + ' ' + parts[2] + ' ' + parts[3]
        return Lecture(lec_identifier,self.al)