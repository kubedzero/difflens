# This is the entry to the project, what a CLI user of python will call
# Used for getting more easily defined CLI args
import argparse
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
    parser.add_argument("--output_modified_files", "-m", help="Output file listing files that have been modified",
                        type=str)
    parser.add_argument("--output_duplicates", "-d", help="Output file listing files that contain matching data",
                        type=str)

    # Define arguments where presence/absence indicates a Boolean. Interprets as true if passed in, false otherwise
    parser.add_argument("--disable_all_hashing", "-p", help="Skip all hashing, comparing on file size alone",
                        action="store_true")
    parser.add_argument("--disable_full_hashing", "-f", help="Skip full hashing, comparing on only partial hashing",
                        action="store_true")

    # Now that we've defined the args to look for, parse them and store their values in the ArgumentParser
    args = parser.parse_args()

    # Configure printing options so the full data_frame prints
    pandas.set_option("display.max_rows", None)
    pandas.set_option("display.max_columns", None)
    pandas.set_option("display.width", None)
    pandas.set_option("display.max_colwidth", None)

    # If the scan directory was given and not the input hash file, try to scan
    if args.scan_directory is not None and args.input_hash_file is None:
        current_dict = compute_diffs(args.scan_directory, disable_all_hashing=args.disable_all_hashing,
                                     disable_full_hashing=args.disable_full_hashing)
        current_data_frame = flatten_dict_to_data_frame(current_dict)

        # Print out some statistics
        print_memory()
        # Get the sum of the number of bytes of all files we read
        # TODO disable this or modify this if all/full hashing is disabled
        # TODO determine processing speed by taking MB/time during hashing, files/time for hashing, files/time for comparing
        print("Total MB of files read: {}".format(current_data_frame["file_size_bytes"].sum() / 1000 / 1000))
    else:
        # Otherwise, the hash file was provided in place of a scan directory. Read it in as a data_frame
        current_data_frame = read_hashes_from_file(args.input_hash_file)

    # One way or another, we should have a current_data_frame now
    # The only analysis we can do on the current_data_frame alone is looking within for duplicates
    if args.output_duplicates is not None:
        print("finding duplicate files based on hash")
        duplicates_data_frame = determine_duplicate_files(current_data_frame)
        write_hashes_to_file(duplicates_data_frame, args.output_duplicates)

    # Next, see if we have a comparison hash file and read in its data_frame if so
    if args.comparison_hash_file is not None:
        print("found a comparison hash file")
        comparison_data_frame = read_hashes_from_file(args.comparison_hash_file)

        # Now we have a current_data_frame and a comparison_data_frame and we can see what to analyze
        # See if we should be looking for deleted files based on relative path
        if args.output_removed_files is not None:
            print("find deleted files")
            deleted_data_frame = determine_removed_files(comparison_data_frame, current_data_frame)
            write_hashes_to_file(deleted_data_frame, args.output_removed_files)

        # See if we should be looking for added files based on relative path
        if args.output_new_files is not None:
            print("find added files")
            added_data_frame = determine_removed_files(current_data_frame, comparison_data_frame)
            write_hashes_to_file(added_data_frame, args.output_new_files)

        # See if we should be looking for modified files based on relative path and hash
        if args.output_modified_files is not None:
            print("find modified files")
            modified_data_frame = determine_modified_files(comparison_data_frame, current_data_frame)
            write_hashes_to_file(modified_data_frame, args.output_modified_files)

    # Write current_data_frame to disk if an output path was provided. Done after analysis since it's already in memory
    if args.output_hash_file is not None:

        if args.input_hash_file is not None:
            print("No changes were made to {}, use that instead of {} as no scan+compute took place".format(
                args.input_hash_file, args.output_hash_file))
            exit(0)
        write_hashes_to_file(current_data_frame, args.output_hash_file)
        exit(0)


# https://stackoverflow.com/questions/419163
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__":
    main(argv[1:])
