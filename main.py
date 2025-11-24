import sys

text_file_path = sys.argv[1]
integer_inputs = [int(x) for x in sys.argv[2:]]

# Read file
try:
    with open(text_file_path, "r") as f:
        text_data = f.read()
except Exception as e:
    print(f"Error reading file: {e}")

