import sys

from InputProcessor import InputProcessor

# check for the minimum amount of arguments
if len(sys.argv) < 9:
    print("not enough arguments given")
    exit()

text_file_path = sys.argv[1]

# handle the integer inputs
try:
    integer_inputs = [int(x) for x in sys.argv[2:]]
except ValueError:
    print("arguments must be integers")
    exit()

# read text file
try:
    with open(text_file_path, "r") as f:
        text_data = f.read()
except Exception as e:
    exit()

# text_data contains the text file date
# integer_inputs contains a list of the rest of the arguments
lines = InputProcessor.process_data(text_data, integer_inputs)

for i in lines:
    print(i)
