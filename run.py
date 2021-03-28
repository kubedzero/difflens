# This is the entry to the project, what a CLI user of Python will call
# Used for getting more easily defined CLI args
import argparse
# Used for printing the Python working directory
from os import getcwd
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
    parser.add_argument("--output_added_files", "-a", help="Output file listing files that have been added", type=str)
    parser.add_argument("--output_modified_files", "-m", help="Output file listing files that have been modified",
                        type=str)
    parser.add_argument("--output_duplicates", "-d", help="Output file listing files that contain matching data",
                        type=str)

    # Define argument where a specific list of strings are allowed
    # https://stackoverflow.com/questions/15836713
    parser.add_argument("--log_level", "-l", help="Set log level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], type=str, default="INFO")

    # Define arguments where an int is expected
    parser.add_argument("--log_update_interval_seconds", "-t",
                        help="Target interval in seconds between log updates when hashing", type=int, default=60)
    parser.add_argument("--log_update_interval_files", "-x", help="Target interval of files hashed between log updates",
                        type=int, default=1000)

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

    executor_logger.warning("Starting diff-lens from current working directory {}".format(getcwd()))

    # If the scan directory was given and not the input hash file, try to scan
    if args.scan_directory is not None and args.input_hash_file is None:
        executor_logger.info(
            "Beginning directory scan and file hash computation of files in {}".format(args.scan_directory))
        byte_count_to_hash = 1000000
        current_dict = compute_diffs(args.scan_directory, io_logger, byte_count_to_hash=byte_count_to_hash,
                                     disable_all_hashing=args.disable_all_hashing,
                                     disable_full_hashing=args.disable_full_hashing,
                                     log_update_interval_seconds=args.log_update_interval_seconds,
                                     log_update_interval_files=args.log_update_interval_files)
        executor_logger.info("Directory scan and file hash computation complete. Flattening output into DataFrame")
        current_data_frame = flatten_dict_to_data_frame(current_dict)
        # Print out stats on memory used
        print_memory(executor_logger)
    else:
        # Otherwise, the hash file was provided in place of a scan directory. Read it in as a data_frame
        executor_logger.info(
            "Reading current_data_frame from file {} rather than directory scan".format(args.input_hash_file))
        current_data_frame = read_hashes_from_file(args.input_hash_file, io_logger, args.disable_full_hashing)

    # One way or another, we should have a current_data_frame now
    # https://stackoverflow.com/questions/15943769
    current_data_frame_rows = len(current_data_frame.index)
    executor_logger.info("Current DataFrame contains {} rows, beginning analysis".format(current_data_frame_rows))

    # The only analysis we can do on the current_data_frame alone is looking within for duplicates
    if args.output_duplicates is not None:
        executor_logger.info("Finding duplicates in Current DataFrame based on file hash")
        duplicates_data_frame = determine_duplicate_files(current_data_frame)
        # https://stackoverflow.com/questions/45759966
        executor_logger.info("Writing Duplicate DataFrame with {} rows across {} groups to disk at {}".format(
            len(duplicates_data_frame.index), duplicates_data_frame["hash"].nunique(), args.output_duplicates))
        write_hashes_to_file(duplicates_data_frame, args.output_duplicates, io_logger,
                             disable_full_hashing=args.disable_full_hashing)

    # Next, see if we have a comparison hash file and read in its data_frame if so
    if args.comparison_hash_file is not None:
        executor_logger.debug("Reading Comparison DataFrame from disk")
        comparison_data_frame = read_hashes_from_file(args.comparison_hash_file, io_logger, args.disable_full_hashing)

        # Now we have a current_data_frame and a comparison_data_frame and we can see what to analyze
        # See if we should be looking for deleted files based on relative path
        if args.output_removed_files is not None:
            executor_logger.info("Finding files in the comparison_data_frame that have been (Re)moved")
            removed_data_frame = determine_removed_files(comparison_data_frame, current_data_frame)
            executor_logger.info(
                "Writing (Re)moved DataFrame with {} rows to disk at {}".format(len(removed_data_frame.index),
                                                                                args.output_removed_files))
            write_hashes_to_file(removed_data_frame, args.output_removed_files, io_logger,
                                 disable_full_hashing=args.disable_full_hashing)

        # See if we should be looking for added files based on relative path
        if args.output_added_files is not None:
            executor_logger.info("Finding files in the comparison_data_frame that have been Added")
            added_data_frame = determine_removed_files(current_data_frame, comparison_data_frame)
            executor_logger.info(
                "Writing Added DataFrame with {} rows to disk at {}".format(len(added_data_frame.index),
                                                                            args.output_added_files))
            write_hashes_to_file(added_data_frame, args.output_added_files, io_logger,
                                 disable_full_hashing=args.disable_full_hashing)

        # See if we should be looking for modified files based on relative path and hash
        if args.output_modified_files is not None:
            executor_logger.info("Finding files with different hashes than their Comparison DataFrame counterparts")
            modified_data_frame = determine_modified_files(comparison_data_frame, current_data_frame)
            executor_logger.info(
                "Writing Modified DataFrame with {} rows to disk at {}".format(len(modified_data_frame.index),
                                                                               args.output_modified_files))
            write_hashes_to_file(modified_data_frame, args.output_modified_files, io_logger, hash_column_exists=False)
    else:
        if args.output_removed_files is not None or args.output_added_files is not None or args.output_modified_files is not None:
            executor_logger.warning(
                "Skipping any Added, Removed, or Modified analysis as no comparison_hash_file was passed in")
    # Write current_data_frame to disk if an output path was provided. Done after analysis since it's already in memory
    if args.output_hash_file is not None:
        # If the input_hash_file arg was also provided, don't bother writing an output file since it would be identical
        if args.input_hash_file is not None:
            executor_logger.info(
                "No changes were made to {}, use that instead of {} as no scan+compute took place".format(
                    args.input_hash_file, args.output_hash_file))
            exit(0)
        executor_logger.info(
            "Writing newly computed file hashes for {} files to disk at {}".format(current_data_frame_rows,
                                                                                   args.output_hash_file))
        write_hashes_to_file(current_data_frame, args.output_hash_file, io_logger,
                             disable_full_hashing=args.disable_full_hashing)
    executor_logger.warning("Shutting down diff-lens")
    exit(0)


# https://stackoverflow.com/questions/419163
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__":
    main(argv[1:])
