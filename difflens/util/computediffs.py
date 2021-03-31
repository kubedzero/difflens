# Used to construct paths or traverse directory trees
from os import path, walk
# Used to track time spent, which allows calculation of processing rates and log intervals
from time import time

# Used for computing the hash of a file on disk
# https://github.com/oconnor663/blake3-py
from blake3 import blake3
# Used to create DataFrames
from pandas import DataFrame

from .commonutils import sanitize_and_validate_directory_path


# Helper to log the progress made during hashing
def log_current_progress(logger, start_time, current_time, bytes_read, files_seen, directories_seen):
    # Calculate stats
    run_time_seconds = current_time - start_time
    run_time_minutes = run_time_seconds / 60
    bytes_read_mb = bytes_read / 1000 / 1000
    processed_mb_per_second = bytes_read_mb / run_time_seconds

    # If processing has taken >5m, switch printout from seconds to minutes for decreased granularity
    file_processing_time = run_time_seconds
    time_unit = "seconds"
    if file_processing_time > 300:
        time_unit = "minutes"
        file_processing_time = run_time_minutes

    # If processing speed is <5 files per second, switch printout to files per minute for increased granularity
    file_processing_rate = files_seen / run_time_seconds
    file_processing_unit = "second"
    if file_processing_rate < 5:
        file_processing_rate = files_seen / run_time_minutes
        file_processing_unit = "minute"

    # Print the variable-unit log line
    logger.info(
        "{:.1f}MB of data read from disk across {} directories & {} files in {:.2f} {} at {:.0f}MBps, "
        "or {:.0f} files per {}".format(bytes_read_mb, directories_seen, files_seen, file_processing_time, time_unit,
                                        processed_mb_per_second, file_processing_rate, file_processing_unit))


# Helper to handle creating or updating a list stored in a dict
def add_or_update_dict_list(dict_to_update, dict_key, string_to_store):
    if dict_key not in dict_to_update:
        dict_to_update[dict_key] = [string_to_store]
    else:
        dict_to_update[dict_key].append(string_to_store)
    return dict_to_update


# Inputs are a BLAKE3 hasher already loaded with the first N bytes of a file stream, the remaining bytes of the file
# stream, the dict to update with the hash output, and the relative path to store in the dict. Compute the
# hexadecimal hash by reading blocks at a time, to avoid exhausting memory. Then store it in the dict with
# {key:full_hash, value:list_of_relative_paths} and then return the updated dict.
def update_full_hash_dict(dict_to_update, relative_path, stream, blake3_hasher):
    # Bytes to read in at a time, 2^20 = 1MB
    # TODO this value was chosen out of a hat. Do performance testing to find the best value
    read_block_size = 2 ** 20
    # Read in chunks to avoid MemoryError exceptions when the full file doesn't fit in memory
    # https://stackoverflow.com/questions/1131220
    while True:
        data = stream.read(read_block_size)
        # Exit the while loop only when there is no more data to read
        if not data:
            break
        # Update the hash with the new non-None data
        blake3_hasher.update(data)
    # Get the hexadecimal 64-character representation of the hash's final state
    hex_hash_string = blake3_hasher.hexdigest()

    # Save the hash and RELATIVE path to the dict, creating a new list if one didn't exist before
    dict_to_update = add_or_update_dict_list(dict_to_update, hex_hash_string, relative_path)
    # Return the updated dict to the caller
    return dict_to_update


# Provided with a starting dict, an absolute and path of a file, its size in bytes, and the amount of bytes to read,
# read the first N bytes from the file to compute the BLAKE3 hash of those bytes. Then determine if the entire file
# was read, or if more remains. Save the result to the dict, where the key is a Tuple of (partial hash,
# file_size_less_than_bytes_to_read?) and the value is either:
# 1. a nested dict of {key:full_hash, value:list_of_relative_paths} updated by a full_hash helper
# 2. a list of relative paths of the files sharing the same partial hash that ALSO is under the hash threshold
# NOTE: The split value structure is in hopes of reducing dict memory footprint
def update_partial_dict(dict_to_update, absolute_path, relative_path, file_size_bytes, byte_count_to_hash,
                        disable_full_hashing):
    # Open the file in read-only, binary format
    # NOTE: ALL processing occurs while the file is open, as the file stream can be passed to a helper for full hashing
    # https://stackabuse.com/file-handling-in-python/
    with open(absolute_path, "rb") as stream:
        # Initialize the hasher that we'll use for partial hashing and CONTINUE using for full hashing
        blake3_hasher = blake3()
        # Update the hasher with the first N bytes of the file
        # NOTE: If a file is 100 bytes, f.read(100) will read the entire file.
        blake3_hasher.update(stream.read(byte_count_to_hash))
        # Get the hexadecimal 64-character representation of the hash
        hex_hash_string = blake3_hasher.hexdigest()

        # Boolean on if the file was smaller than the read buffer. If True, the file was read in its entirety.
        file_fully_hashed = file_size_bytes <= byte_count_to_hash
        # Make the dictKey a Tuple with schema (string:partial hash, bool:file_size_less_than_bytes_to_read?)
        dict_key = (hex_hash_string, file_fully_hashed)

        if file_fully_hashed:
            # The full file was read if file_fully_hashed=True. No more hashing necessary, store in a list at this level
            dict_to_update = add_or_update_dict_list(dict_to_update, dict_key, relative_path)
        else:
            # Proceed with hashing the full file if the caller did not indicate that full hashing should be skipped
            if not disable_full_hashing:
                if dict_key not in dict_to_update:
                    dict_to_update[dict_key] = update_full_hash_dict({}, relative_path, stream, blake3_hasher)
                else:
                    dict_to_update[dict_key] = update_full_hash_dict(dict_to_update[dict_key], relative_path, stream,
                                                                     blake3_hasher)
            else:
                # Otherwise finish processing this file by adding its partial hash and name to the dict
                dict_to_update = add_or_update_dict_list(dict_to_update, hex_hash_string, relative_path)
        # Return the updated dict to the caller
        return dict_to_update


# Entry point for hashing computation. Given a relative or absolute input path, find files it contains and determine
# their size, partial and/or full hash, saving those values to a dict. Finally, return that dict
# If disable_all_hashing is set to True, only the file size has to match to be considered a duplicate
# If disable_full_hashing is set to True, only the partial hash has to match to be considered a duplicate
def compute_diffs(input_path, logger, byte_count_to_hash, disable_all_hashing, disable_full_hashing,
                  log_update_interval_seconds, log_update_interval_files):
    # Log the hashing state
    logger.debug("Disable all hashing, using just file size? {}. "
                 "Disable full hashing, using just the first {:.2f} MB? {}.".format(disable_all_hashing,
                                                                                    byte_count_to_hash / 1000 / 1000,
                                                                                    disable_full_hashing))
    # Input directory, which we'll modify to be an absolute path without a trailing slash (how Python wants it)
    path_to_process = sanitize_and_validate_directory_path(input_path, logger)

    # Create the top-level dict in which we'll store duplicates. Dict keys at this level are file sizes in bytes
    file_duplicates_dict = {}
    # Initialize counters
    files_seen = last_files_seen = directories_seen = bytes_read = bytes_total = 0
    # https://www.tutorialspoint.com/python/time_time.htm
    start_time = last_logger_time = time()

    # https://stackoverflow.com/questions/53123867
    # Process top-down. Adding topdown=False to the walk() arguments would read from the deepest structure upwards
    # dir_path will update to the directory we're currently scanning. It is an absolute path
    # dirs is a list of subdirectories in the current dir_path
    # files is a list of file names in the current dir_path
    for dir_path, dirs, files in walk(path_to_process):
        directories_seen += 1
        # Iterate through files that are immediate children in the current dir_path
        for file in files:
            # Log an update if enough files have been seen since the last update, or if the time interval was reached
            current_time = time()
            if (current_time - last_logger_time) > log_update_interval_seconds or (
                    files_seen - last_files_seen) > log_update_interval_files:
                log_current_progress(logger, start_time, current_time, bytes_read, files_seen, directories_seen)
                last_logger_time = current_time
                last_files_seen = files_seen

            files_seen += 1
            # TODO add new input argument for an excludes file used to skip certain paths or extensions
            # Construct the absolute path that we'll need to access the file
            absolute_file_path = path.join(dir_path, file)
            # Skip symbolic link access to avoid accessing broken symlinks causing FileNotFoundError exceptions
            if path.islink(absolute_file_path):
                logger.warn("Found a symbolic link at path {}, skipping".format(absolute_file_path))
                continue
            # Construct the relative path based on user input that we'll end up storing in the dict
            # https://stackoverflow.com/questions/1192978
            input_file_path = path.relpath(absolute_file_path)
            # Get the size of the file, in Bytes
            # https://stackoverflow.com/questions/6591931
            file_size_bytes = path.getsize(absolute_file_path)
            bytes_total += file_size_bytes
            # Proceed with partial or full hashing if disable_all_hashing=False
            if not disable_all_hashing:
                if not disable_full_hashing:
                    bytes_read += file_size_bytes
                else:
                    bytes_read += min(file_size_bytes, byte_count_to_hash)

                # Check if the fileBytesDict already contains an entry for the current file's size
                if file_size_bytes not in file_duplicates_dict:
                    # If no entry existed, create a new dict as a value and populate it using a helper
                    file_duplicates_dict[file_size_bytes] = update_partial_dict({}, absolute_file_path, input_file_path,
                                                                                file_size_bytes, byte_count_to_hash,
                                                                                disable_full_hashing)
                else:
                    # An entry already existed as the value, so pass it to the helper to update
                    file_duplicates_dict[file_size_bytes] = update_partial_dict(file_duplicates_dict[file_size_bytes],
                                                                                absolute_file_path, input_file_path,
                                                                                file_size_bytes, byte_count_to_hash,
                                                                                disable_full_hashing)
            else:
                # Otherwise finish processing this file by adding its bytes to the dict
                file_duplicates_dict = add_or_update_dict_list(file_duplicates_dict, file_size_bytes,
                                                               input_file_path)
        # We've exited the for loop for the current dir_path's files, onto the next dir_path

    # Now that we're done traversing, print out summarized information
    log_current_progress(logger, start_time, time(), bytes_read, files_seen, directories_seen)
    if disable_all_hashing or disable_full_hashing:
        bytes_saved_mb = (bytes_total - bytes_read) / 1000 / 1000
        logger.info(
            "By partially/fully disabling hashing, "
            "difflens skipped reading {:.0f}MB from files on disk under {}".format(bytes_saved_mb, input_path))
    # Return the dict to the caller
    return file_duplicates_dict


# Provided with the dict computed earlier, parse it into a flattened DataFrame for analysis
def flatten_dict_to_data_frame(file_duplicates_dict):
    # Define a list which will contain the flattened rows to write
    # Schema: file_path::string, full_hash::string, file_size_bytes::int
    # TODO add modified date, hashing date?
    flat_list = []

    # Flatten the data by iterating through the nested dicts in the correct way
    # Level zero contains file size as the key
    for level_zero_key, level_zero_value in file_duplicates_dict.items():
        if isinstance(level_zero_value, dict):
            # Level one contains the Tuple of (partial_hash, file_fully_hashed?) as the key
            for level_one_key, level_one_value in level_zero_value.items():
                if isinstance(level_one_value, dict):
                    # Level two contains the full hash as the key, and guaranteed to have a list of files as the value
                    for level_two_key, level_two_value in level_one_value.items():
                        for list_item in level_two_value:
                            flat_list.append([list_item, level_two_key, level_zero_key])
                else:
                    # If the value wasn't a dict, then it's a list of files.
                    # This occurs when the partial hash was actually a full hash due to the file being small
                    # or when hashing was stopped early due to disable_full_hash=True
                    for list_item in level_one_value:
                        # Handle cases where key is a Tuple of the hash and file_fully_read indicator OR a hash string
                        if isinstance(level_one_key, tuple):
                            flat_list.append([list_item, level_one_key[0], level_zero_key])
                        else:
                            flat_list.append([list_item, level_one_key, level_zero_key])
        else:
            # if the value wasn't a dict, then it's a list of files
            for list_item in level_zero_value:
                flat_list.append([list_item, "not_computed", level_zero_key])

    # Input the flat-formatted list into a DataFrame while specifying column names
    # https://stackoverflow.com/questions/13784192
    data_frame = DataFrame(flat_list, columns=["relative_path", "hash", "file_size_bytes"])
    return data_frame
