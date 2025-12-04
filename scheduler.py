import sys
import argparse
from parser import parse_file
from solver import solve

def main():
    #Define parser for command line arguments
    parser = argparse.ArgumentParser(description="University Course Scheduler")
    parser.add_argument("filename", help="Input file path")
    parser.add_argument("w_minfilled", type=float)
    parser.add_argument("w_pref", type=float)
    parser.add_argument("w_pair", type=float)
    parser.add_argument("w_secdiff", type=float)
    parser.add_argument("pen_lecturemin", type=float, help="Unused in standard spec but required by args")
    parser.add_argument("pen_tutorialmin", type=float, help="Unused")
    parser.add_argument("pen_notpaired", type=float)
    parser.add_argument("pen_section", type=float)

    #Read command line
    args = parser.parse_args()

    #Parse input file
    print("Parsing input file...")
    problem = parse_file(args.filename)
    print(f"Parsed {len(problem.lectures)} lectures and {len(problem.tutorials)} tutorials.")

    #Collect numerical arguments
    weights = (args.w_minfilled, args.w_pref, args.w_pair, args.w_secdiff, args.pen_notpaired, args.pen_section)

    #Do the search
    print("Starting solver...")
    solution, cost = solve(problem, weights)

    #Print solution in proper format if a solution exists
    if solution:
        print(f"Eval-value: {int(cost)}")
        # Sort assignments: Alphabetical by Course ID
        sorted_assignments = sorted(solution.assignments.items(), key=lambda x: x[0].id)
        for course, slot in sorted_assignments:
            print(f"{course.id} : {slot.id}")
    else:
        print("No solution found.")

if __name__ == "__main__":
    main()
