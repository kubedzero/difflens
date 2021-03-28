# This is the entry to the project, what a CLI user of python will call
# Used for getting more easily defined CLI args
import argparse
from os import chdir
# Used for getting the list of arguments with which the program was called
from sys import argv

# Used for configuring DataFrame printing options
import pandas

from common_utils import print_memory
from compare_files import determine_duplicate_files, determine_modified_files, determine_removed_files
from compute_diffs import compute_diffs, flatten_dict_to_data_frame
from hash_file_io import write_hashes_to_file, read_hashes_from_file


def main(args):
    # https://docs.python.org/3/library/argparse.html
    # https://stackabuse.com/command-line-arguments-in-python/
    # Set up the argparse object that defines and handles program input arguments
    parser = argparse.ArgumentParser(description="A program to inspect collections of files for differences")

    # Initialize a group to force either-or argument behavior
    # https://stackoverflow.com/questions/11154946/
    arg_group = parser.add_mutually_exclusive_group(required=True)
    arg_group.add_argument("--scan_directory", "-s", help="Path in which to look for files", type=str)
    arg_group.add_argument("--input_hash_file", "-i",
                           help="Input file for new hash values, if we want to skip scanning",
                           type=str)
    # Define arguments where a string is expected
    parser.add_argument("--comparison_hash_file", "-c", help="Path to delimited file containing old hash values",
                        type=str)
    parser.add_argument("--output_hash_file", "-o", help="Output file for newly computed hash values", type=str)
    parser.add_argument("--output_removed_files", "-r", help="Output file listing files that have been removed",
                        type=str)
    parser.add_argument("--output_new_files", "-n", help="Output file listing files that have been added", type=str)
    parser.add_argument("--output_modified-files", "-m", help="Output file listing files that have been modified",
                        type=str)
    parser.add_argument("--output_duplicates", "-d", help="Output file listing files that contain matching data",
                        type=str)

    # Define arguments where presence/absence indicates a Boolean. Interprets as true if passed in, false otherwise
    parser.add_argument("--skip_all_hashing", "-p", help="Skip all hashing, comparing on file size alone",
                        action="store_true")
    parser.add_argument("--skip_full_hashing", "-f", help="Skip full hashing, comparing on only partial hashing",
                        action="store_true")

    # Now that we've defined the args to look for, parse them and store their values in the ArgumentParser
    args = parser.parse_args()

    # Configure printing options so the full data_frame prints
    pandas.set_option("display.max_rows", None)
    pandas.set_option("display.max_columns", None)
    pandas.set_option("display.width", None)
    pandas.set_option("display.max_colwidth", None)

    # https://www.geeksforgeeks.org/python-os-chdir-method/
    print("computing diff dicts")
    # Simulate running an old versus a new by choosing two different directories while keeping the relative path equal
    chdir("/Users/kz/TestDir")
    shared_relative_path = "."
    dict_to_write = compute_diffs(shared_relative_path)
    chdir("/Users/kz/TestDir 2")
    dict_to_write_new = compute_diffs(shared_relative_path)

    print("converting to dataframe")
    output_data_frame = flatten_dict_to_data_frame(dict_to_write)
    output_data_frame_new = flatten_dict_to_data_frame(dict_to_write_new)

    print("writing dataframes to disk")
    write_hashes_to_file(output_data_frame, "/tmp/old.tsv")
    write_hashes_to_file(output_data_frame_new, "/tmp/new.tsv")

    print("reading dataframes from disk")
    input_old = read_hashes_from_file("/tmp/old.tsv")
    input_new = read_hashes_from_file("/tmp/new.tsv")

    # confirm the dataframe we create from tabular data matches the one we never exported
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.equals.html
    # print("old output equals read?", output_data_frame.equals(input_old))
    # print("new output equals read?", output_data_frame_new.equals(input_new))
    # TODO determine processing speed by taking MB/time during hashing, files/time for hashing, files/time for comparing

    print_memory()
    # Get the sum of the number of bytes of all files we read
    print("Total MB of files read: {}".format(input_new["file_size_bytes"].sum() / 1000 / 1000))

    print("find deleted files")
    deleted_data_frame = determine_removed_files(input_old, input_new)
    # print(deleted_data_frame)

    print("find added files")
    added_data_frame = determine_removed_files(input_new, input_old)
    # print(added_data_frame)

    print("find modified files")
    modified_data_frame = determine_modified_files(input_old, input_new)
    # print(modified_data_frame)

    print("find duplicate files")
    duplicates_data_frame = determine_duplicate_files(input_new)
    # print(duplicates_data_frame)


# https://stackoverflow.com/questions/419163
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__":
    main(argv[1:])
