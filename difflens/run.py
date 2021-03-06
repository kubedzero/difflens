# This is the entry to the project, what a CLI user of Python will call
# Used for getting more easily defined CLI args
import argparse
# Used for printing the Python working directory
from os import getcwd, getpid

# Used to get memory information
from psutil import Process

from difflens.util.compareMode import CompareMode
# Different import styles yield different errors in different environments:
# (1) ImportError: attempted relative import with no known parent package
# (2) ModuleNotFoundError: No module named 'difflens'
# (3) ModuleNotFoundError: No module named 'util'
# NOTE: From CLI, running module-style `python3 -m difflens.run` (or `python3 -m difflens` when __main__.py exists):
# - WILL WORK when imports are relative, i.e. `from .util.xyz`
# - WILL WORK when imports are absolute, i.e. `from difflens.util.xyz`
# - WILL NOT WORK when imports are (partial?) absolute, i.e. `from util.xyz` (3)
# NOTE: From CLI, running file-style `python3 difflens/run.py`:
# - WILL NOT WORK when imports are relative, i.e. `from .util.xyz` (1)
# - WILL NOT WORK when imports are absolute, i.e. `from difflens.util.xyz` (2)
# - WILL NOT WORK when imports are (partial?) absolute, i.e. `from util.xyz` (2)
# NOTE: From PyCharm, running this module's `main()` function at the bottom:
# - WILL NOT WORK when imports are relative, i.e. `from .util.xyz` (1). Fix by changing Run Config to module
# - WILL WORK when imports are absolute, i.e. `from difflens.util.xyz`
# - WILL WORK when imports are (partial?) absolute, i.e. `from util.xyz`
# NOTE: From `pip3 install difflens.whl && difflens` on Linux:
# - WILL WORK when imports are relative, i.e. `from .util.xyz`
# - WILL WORK when imports are absolute, i.e. `from difflens.util.xyz`
# - WILL NOT WORK when imports are (partial?) absolute, i.e. `from util.xyz` (3)
from difflens.util.comparefiles import determine_duplicate_files, determine_modified_files, determine_removed_files
from difflens.util.computediffs import compute_diffs, flatten_dict_to_data_frame
from difflens.util.hashfileio import write_hashes_to_file, read_hashes_from_files
from difflens.util.loghelper import get_logger_with_name
from difflens.util.pathExcluder import PathExcluder


# Set up the argparse object that defines and handles program input arguments
def configure_argument_parser():
    # https://docs.python.org/3/library/argparse.html
    # https://stackabuse.com/command-line-arguments-in-python/
    parser = argparse.ArgumentParser(description="A program to inspect collections of files for differences")

    # Initialize a group to force either-or argument behavior
    # https://stackoverflow.com/questions/11154946/
    arg_group = parser.add_mutually_exclusive_group(required=True)
    arg_group.add_argument("--scan-directory", "-s", help="Path in which to look for files", type=str)
    # action="append" allows this arg to return as a list when passed multiple times as input, or None
    # https://stackoverflow.com/questions/36166225
    arg_group.add_argument("--input-hash-file", "-i",
                           help="Input file for new hash values if live directory scanning should be skipped",
                           type=str, action="append")
    # Define arguments where a string is expected
    parser.add_argument("--comparison-hash-file", "-c", help="Path to delimited file containing old hash values",
                        type=str)
    parser.add_argument("--output-hash-file", "-o", help="Output file for newly computed hash values", type=str)
    parser.add_argument("--output-removed-files", "-r", help="Output file listing files that have been removed",
                        type=str)
    parser.add_argument("--output-added-files", "-a", help="Output file listing files that have been added", type=str)
    parser.add_argument("--output-modified-files", "-m", help="Output file listing files that have been modified",
                        type=str)
    parser.add_argument("--output-duplicates", "-d", help="Output file listing files that contain matching data",
                        type=str)
    parser.add_argument("--exclude-file-extension", "-e",
                        help="File extension such as '*.nfo' that should not be scanned", type=str, action="append")
    parser.add_argument("--exclude-relative-path", "-y",
                        help="Relative dir such as './foo/bar' that should not be scanned", type=str, action="append")

    # Define argument where a specific list of strings are allowed
    # https://stackoverflow.com/questions/15836713
    parser.add_argument("--log-level", "-l", help="Set log level",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], type=str, default="INFO")

    # Define arguments where an int is expected
    parser.add_argument("--log-update-interval-seconds", "-t",
                        help="Target interval in seconds between log updates when hashing", type=int, default=30)
    parser.add_argument("--log-update-interval-files", "-x", help="Target interval of files hashed between log updates",
                        type=int, default=10000)

    # Define argument where a specific list of options are allowed
    # https://stackoverflow.com/questions/15836713
    parser.add_argument("--compare-mode", "-p", help="Set comparison mode to full file hash, partial file hash, or "
                                                     "file size only",
                        choices=[CompareMode.FULL.value, CompareMode.PARTIAL.value, CompareMode.SIZE.value],
                        type=str, default=CompareMode.FULL.value)

    return parser


def main():
    # Set up the argparse object that defines and handles program input arguments
    parser = configure_argument_parser()
    args = parser.parse_args()

    # Initialize the loggers for this project
    # TODO make helpers into Classes and initialize them with their own loggers to avoid passthrough
    executor_logger = get_logger_with_name("Executor", args.log_level)
    io_logger = get_logger_with_name("IO", args.log_level)

    # Set the compare mode to the hash style we'll use: full-hash, partial-hash, or file-size
    compare_mode = args.compare_mode

    executor_logger.warning("Starting difflens from current working directory {}".format(getcwd()))

    # If the scan directory was given and not the input hash file, try to scan
    if args.scan_directory is not None and args.input_hash_file is None:
        executor_logger.info(
            "Beginning directory scan and file hash computation of files in {} using compare_mode {}".format(
                args.scan_directory, compare_mode))
        byte_count_to_hash = 1000000
        path_excluder = PathExcluder(args.exclude_file_extension, args.exclude_relative_path, args.log_level)
        # TODO this isn't really computing diffs, so rename it to something else, maybe compute_hash or something
        current_dict = compute_diffs(args.scan_directory, io_logger, byte_count_to_hash=byte_count_to_hash,
                                     compare_mode=compare_mode,
                                     log_update_interval_seconds=args.log_update_interval_seconds,
                                     log_update_interval_files=args.log_update_interval_files,
                                     path_excluder=path_excluder)
        executor_logger.info("Directory scan and file hash computation complete. Flattening output into DataFrame")
        current_data_frame = flatten_dict_to_data_frame(current_dict)
        # Print out stats on memory used
        # https://stackoverflow.com/questions/938733
        process = Process(getpid())
        # https://stackoverflow.com/questions/455612
        executor_logger.info("RAM used by Python process: {:.1f}MB".format(process.memory_info().rss / 1000 / 1000))
    else:
        # Otherwise, the hash files were provided in place of a scan directory. Read them in as data_frames,
        # merging with each other if there are multiple
        io_logger.info(
            "Reading current_data_frame from file(s) {} rather than directory scan".format(args.input_hash_file))
        current_data_frame = read_hashes_from_files(args.input_hash_file, io_logger, compare_mode)
        duplicate_file_names = determine_duplicate_files(current_data_frame, "relative_path", ["relative_path"])
        # https://stackoverflow.com/questions/19828822
        if not duplicate_file_names.empty:
            executor_logger.warning("Input Hash Files contained {} colliding relative paths! "
                                    "Confirm the inputs contain expected data.".format(len(duplicate_file_names.index)))

    # The current_data_frame should now be loaded, either from scanning or reading in a file.
    # https://stackoverflow.com/questions/15943769
    current_data_frame_rows = len(current_data_frame.index)
    # Write current_data_frame to disk if an output path was provided.
    if args.output_hash_file is not None:
        # If only one instance of input-hash-file was passed in, this would do nothing. Otherwise, we're in concat mode
        # and the output is unique content that should be saved
        if args.input_hash_file is not None and len(args.input_hash_file) == 1:
            executor_logger.info(
                "Desired output {} would be identical to {}, use that instead as no scan+compute took place".format(
                    args.output_hash_file, args.input_hash_file[0]))
        else:
            io_logger.info(
                "Writing newly computed {} for {} files to disk at {}".format(compare_mode, current_data_frame_rows,
                                                                              args.output_hash_file))
            write_hashes_to_file(current_data_frame, args.output_hash_file, io_logger, compare_mode)

    executor_logger.info("Beginning analysis of Current DataFrame with {} rows".format(current_data_frame_rows))

    # If CLI arg is set, perform the only analysis that can be done without a comparison file: finding duplicates
    if args.output_duplicates is not None:
        # Handle when all hashing is disabled and a diff can only occur on file size
        if compare_mode == CompareMode.SIZE.value:
            duplicate_field = "file_size_bytes"
            output_schema = [duplicate_field, "relative_path"]
        else:
            duplicate_field = "hash"
            output_schema = [duplicate_field, "relative_path", "file_size_bytes"]
        executor_logger.info("Finding duplicates in Current DataFrame based on {}".format(duplicate_field))
        duplicates_data_frame = determine_duplicate_files(current_data_frame, duplicate_field, output_schema)
        # https://stackoverflow.com/questions/45759966
        # https://www.geeksforgeeks.org/how-to-count-distinct-values-of-a-pandas-dataframe-column/
        io_logger.info("Writing Duplicate DataFrame with {} rows across {} groups to disk at {}".format(
            len(duplicates_data_frame.index), len(duplicates_data_frame[duplicate_field].value_counts()),
            args.output_duplicates))
        write_hashes_to_file(duplicates_data_frame, args.output_duplicates, io_logger, compare_mode)

    # If the path to a comparison_hash_file is provided by the CLI, read it in for comparison-based analysis
    if args.comparison_hash_file is not None:
        io_logger.info("Reading Comparison DataFrame from disk at {}".format(args.comparison_hash_file))
        comparison_data_frame = read_hashes_from_files([args.comparison_hash_file], io_logger, compare_mode)

        # Both current_data_frame and comparison_data_frame are loaded into memory, begin analysis

        # If CLI arg is set, look for deleted files based on relative path
        if args.output_removed_files is not None:
            executor_logger.info("Finding files in the comparison_data_frame that have been (Re)moved")
            removed_data_frame = determine_removed_files(comparison_data_frame, current_data_frame)
            io_logger.info(
                "Writing (Re)moved DataFrame with {} rows to disk at {}".format(len(removed_data_frame.index),
                                                                                args.output_removed_files))
            write_hashes_to_file(removed_data_frame, args.output_removed_files, io_logger, compare_mode)

        # If CLI arg is set, look for added files based on relative path
        if args.output_added_files is not None:
            executor_logger.info("Finding files in the comparison_data_frame that have been Added")
            added_data_frame = determine_removed_files(current_data_frame, comparison_data_frame)
            io_logger.info("Writing Added DataFrame with {} rows to disk at {}".format(len(added_data_frame.index),
                                                                                       args.output_added_files))
            write_hashes_to_file(added_data_frame, args.output_added_files, io_logger, compare_mode)

        # If CLI arg is set, look for modified files based on relative path and hash
        if args.output_modified_files is not None:
            executor_logger.info("Finding files with different hashes than their Comparison DataFrame counterparts")
            modified_data_frame = determine_modified_files(comparison_data_frame, current_data_frame)
            io_logger.info("Writing Modified DataFrame with {} rows to disk at {}".format(
                len(modified_data_frame.index), args.output_modified_files))
            write_hashes_to_file(modified_data_frame, args.output_modified_files, io_logger, compare_mode)
    else:
        if args.output_removed_files is not None \
                or args.output_added_files is not None \
                or args.output_modified_files is not None:
            executor_logger.warning(
                "Skipping any Added, Removed, or Modified analysis as no comparison_hash_file was passed in")
    executor_logger.warning("Shutting down difflens")
    exit(0)


# Used for running via file mode, aka python difflens/run.py, or module mode, aka python -m difflens.run
# NOTE that it may encounter an ImportError in file mode if the PYTHONPATH is not set correctly.
# PyCharm seems to take care of this by updating the PYTHONPATH before executing a Run Configuration
if __name__ == "__main__":
    main()
