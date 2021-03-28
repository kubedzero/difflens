# This is the entry to the project, what a CLI user of Python will call
# Used for getting more easily defined CLI args
import argparse
# Used for getting the list of arguments with which the program was called
from sys import argv

from common_utils import print_memory
from compare_files import determine_duplicate_files, determine_modified_files, determine_removed_files
from compute_diffs import compute_diffs, flatten_dict_to_data_frame
from hash_file_io import write_hashes_to_file, read_hashes_from_file
from log_helper import get_logger_with_name


# Set up the argparse object that defines and handles program input arguments
def configure_argument_parser():
    # https://docs.python.org/3/library/argparse.html
    # https://stackabuse.com/command-line-arguments-in-python/
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

    # Define argument where a specific list of strings are allowed
    # https://stackoverflow.com/questions/15836713
    parser.add_argument("--log_level", "-l", help="Set log level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], type=str, default="INFO")

    # Define arguments where presence/absence indicates a Boolean. Interprets as true if passed in, false otherwise
    parser.add_argument("--disable_all_hashing", "-p", help="Skip all hashing, comparing on file size alone",
                        action="store_true")
    parser.add_argument("--disable_full_hashing", "-f", help="Skip full hashing, comparing on only partial hashing",
                        action="store_true")
    return parser


# NOTE: PyCharm may think args is not used, but parser.parse_args() needs it here
def main(args):
    # Set up the argparse object that defines and handles program input arguments
    parser = configure_argument_parser()
    args = parser.parse_args()

    # Initialize the loggers for this project
    # TODO make helpers into Classes and initialize them with their own loggers to avoid passthrough
    executor_logger = get_logger_with_name("Executor", args.log_level)
    io_logger = get_logger_with_name("IO", args.log_level)

    executor_logger.warning("Beginning execution of diff-lens")

    # If the scan directory was given and not the input hash file, try to scan
    if args.scan_directory is not None and args.input_hash_file is None:
        executor_logger.info("Beginning directory scan and file hash computation")
        byte_count_to_hash = 1000000
        current_dict = compute_diffs(args.scan_directory, io_logger, byte_count_to_hash=byte_count_to_hash,
                                     disable_all_hashing=args.disable_all_hashing,
                                     disable_full_hashing=args.disable_full_hashing)
        executor_logger.info("Directory scan and file hash computation complete. Flattening output into DataFrame")
        current_data_frame = flatten_dict_to_data_frame(current_dict)

        # Print out some statistics
        print_memory(executor_logger)
        # Get the sum of the number of bytes of all files we read
        if not args.disable_all_hashing:
            if not args.disable_full_hashing:
                executor_logger.info(
                    "Total MB of files read: {}".format(current_data_frame["file_size_bytes"].sum() / 1000 / 1000))
            else:
                executor_logger.info(
                    "Partial hashes used. Maximum MB of files read: {}".format(
                        len(current_data_frame.index) * byte_count_to_hash))
        # TODO determine processing speed by taking MB/time during hashing, files/time for hashing, files/time for comparing
    else:
        # Otherwise, the hash file was provided in place of a scan directory. Read it in as a data_frame
        executor_logger.debug("Reading current_data_frame from file rather than directory scan")
        current_data_frame = read_hashes_from_file(args.input_hash_file, io_logger)

    # One way or another, we should have a current_data_frame now
    executor_logger.info("Current DataFrame contains {} rows".format(len(current_data_frame.index)))
    # The only analysis we can do on the current_data_frame alone is looking within for duplicates
    if args.output_duplicates is not None:
        executor_logger.info("Finding duplicate files in current_data_frame based on hash")
        duplicates_data_frame = determine_duplicate_files(current_data_frame)
        executor_logger.debug("Writing duplicate file list to disk")
        write_hashes_to_file(duplicates_data_frame, args.output_duplicates, io_logger)

    # Next, see if we have a comparison hash file and read in its data_frame if so
    if args.comparison_hash_file is not None:
        executor_logger.debug("Reading comparison hash file from disk")
        comparison_data_frame = read_hashes_from_file(args.comparison_hash_file, io_logger)

        # Now we have a current_data_frame and a comparison_data_frame and we can see what to analyze
        # See if we should be looking for deleted files based on relative path
        if args.output_removed_files is not None:
            executor_logger.info("Finding files in the comparison_data_frame that have been (re)moved")
            removed_data_frame = determine_removed_files(comparison_data_frame, current_data_frame)
            executor_logger.info("(Re)moved DataFrame contains {} rows".format(len(removed_data_frame.index)))
            executor_logger.debug("Writing (re)moved file list to disk")
            write_hashes_to_file(removed_data_frame, args.output_removed_files, io_logger)

        # See if we should be looking for added files based on relative path
        if args.output_new_files is not None:
            executor_logger.info("Finding files in the comparison_data_frame that have been added")
            added_data_frame = determine_removed_files(current_data_frame, comparison_data_frame)
            executor_logger.info("Added DataFrame contains {} rows".format(len(added_data_frame.index)))
            executor_logger.debug("Writing added file list to disk")
            write_hashes_to_file(added_data_frame, args.output_new_files, io_logger)

        # See if we should be looking for modified files based on relative path and hash
        if args.output_modified_files is not None:
            executor_logger.info("Finding files with different hashes than their comparison_data_frame counterparts")
            modified_data_frame = determine_modified_files(comparison_data_frame, current_data_frame)
            executor_logger.info("Modified DataFrame contains {} rows".format(len(modified_data_frame.index)))
            executor_logger.debug("Writing modified file list to disk")
            write_hashes_to_file(modified_data_frame, args.output_modified_files, io_logger)

    # Write current_data_frame to disk if an output path was provided. Done after analysis since it's already in memory
    if args.output_hash_file is not None:
        # If the input_hash_file arg was also provided, don't bother writing an output file since it would be identical
        if args.input_hash_file is not None:
            executor_logger.info(
                "No changes were made to {}, use that instead of {} as no scan+compute took place".format(
                    args.input_hash_file, args.output_hash_file))
            exit(0)
        executor_logger.debug("Writing newly computed file hashes to disk")
        write_hashes_to_file(current_data_frame, args.output_hash_file, io_logger)
    executor_logger.warning("Shutting down diff-lens")
    exit(0)


# https://stackoverflow.com/questions/419163
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__":
    main(argv[1:])
