from os import path, walk
from time import time

import pandas
from blake3 import blake3

import common_utils


# Helper to log the progress made during hashing
def log_current_progress(logger, start_time, current_time, bytes_read, files_seen, directories_seen):
    run_time = time() - start_time
    bytes_read_mb = bytes_read / 1000 / 1000
    processed_mb_per_second = bytes_read_mb / run_time
    processed_files_per_second = files_seen / run_time
    logger.info("{:.1f} MB of data read from disk across {} directories & {} files in {:.2f} seconds at {:.1f}MBps, "
                "or {:.1f} files per second".format(bytes_read_mb, directories_seen, files_seen, run_time,
                                                    processed_mb_per_second, processed_files_per_second))


# Helper to handle creating or updating a list stored in a dict
def add_or_update_dict_list(dict_to_update, dict_key, string_to_store):
    if dict_key not in dict_to_update:
        dict_to_update[dict_key] = [string_to_store]
    else:
        dict_to_update[dict_key].append(string_to_store)
    return dict_to_update


# Provided with a starting dict, an absolute path of a file, and a relative path of the same file,
# compute the BLAKE3 hash. Then save it to the dict with the key as the hash in hexadecimal form
# and the value as a list of relative paths sharing the same hash. Finally, return the updated dict.
def update_full_hash_dict(dict_to_update, absolute_path, relative_path, enable_multithreading):
    # Open the file in read-only, binary format
    # https://stackabuse.com/file-handling-in-python/
    with open(absolute_path, "rb") as f:
        # Get the hexadecimal 64-character representation of the hash
        # https://github.com/oconnor663/blake3-py
        hex_hash_string = blake3(f.read(), multithreading=enable_multithreading).hexdigest()

    # Save the hash and RELATIVE path to the dict, creating a new list if one didn't exist before
    dict_to_update = add_or_update_dict_list(dict_to_update, hex_hash_string, relative_path)
    # Return the updated dict to the caller
    return dict_to_update


# Provided with a starting dict, an absolute path of a file, a relative path of the same file,
# the size of the input file in bytes, and the amount of bytes to read, read the first N bytes
# from the file to compute the BLAKE3 hash of those bytes. Then determine if the entire file was
# read, or if more remains. Save the result to the dict, where the key is a Tuple of the partial hash
# and whether or not the file was fully hashed, and the value is either a nested dict of the
# full hash OR a list of the files sharing the same partial hash that ALSO is under the hash threshold
# NOTE: the split structure between the files needing further hash and the small files is in hopes of
# reducing memory footprint
def update_partial_dict(dict_to_update, absolute_path, relative_path, file_size_bytes, byte_count_to_hash,
                        enable_multithreading, disable_full_hashing):
    # Open the file in read-only, binary format
    # https://stackabuse.com/file-handling-in-python/
    with open(absolute_path, "rb") as f:
        # Get the hexadecimal 64-character representation of the first N bytes of the file
        # https://github.com/oconnor663/blake3-py
        # NOTE: If a file is 100 bytes, f.read(100) will read the entire file.
        hex_hash_string = blake3(f.read(byte_count_to_hash)).hexdigest()

    # Boolean on whether or not the file was smaller than the read buffer. This tells us if we fully read the file
    file_fully_hashed = file_size_bytes <= byte_count_to_hash
    # Make the dictKey a tuple indicating the hash value, but also whether or not we fully read the file
    dict_key = (hex_hash_string, file_fully_hashed)

    if file_fully_hashed:
        # If the file was fully hashed, we don't need additional hashing since we already covered the full file.
        # Instead of making another nested dict with a repeated hash, just store the list at this level
        dict_to_update = add_or_update_dict_list(dict_to_update, dict_key, relative_path)
    else:
        # If we plan to diff on more than just the hash of the first N bytes of the file, proceed
        if not disable_full_hashing:
            # If false, continue by hashing the full file
            if dict_key not in dict_to_update:
                dict_to_update[dict_key] = update_full_hash_dict({}, absolute_path, relative_path,
                                                                 enable_multithreading)
            else:
                dict_to_update[dict_key] = update_full_hash_dict(dict_to_update[dict_key], absolute_path,
                                                                 relative_path,
                                                                 enable_multithreading)
        else:
            # Otherwise finish processing this file by adding its partial hash and name to the dict
            dict_to_update = add_or_update_dict_list(dict_to_update, hex_hash_string, relative_path)
    # Return the updated dict to the caller
    return dict_to_update


# Entry point for our hash computation. Given a relative or absolute input path, find files it contains and determine
# their size, partial and/or full hash, saving those values to a dict. Finally, return that dict
# enable_multithreading is True by default because we assume files being hashed are >1MB and therefore
# most efficiently hashed in a multi-threaded manner.
# If disable_all_hashing is set to True, only the file size has to match to be considered a duplicate
# If disable_full_hashing is set to True, only the partial hash has to match to be considered a duplicate
# TODO add logging that looks at last logged time and only outputs if it's been X minutes.
#  Processed X directories/files/mb
def compute_diffs(input_path, logger, byte_count_to_hash=1000000, enable_multithreading=True, disable_all_hashing=False,
                  disable_full_hashing=False):
    # Log our hashing state
    logger.info("Disable all hashing, using just file size? {}. "
                "Disable full hashing, using just the first {:.2f} MB? {}.".format(disable_all_hashing,
                                                                                   byte_count_to_hash / 1000 / 1000,
                                                                                   disable_full_hashing))
    # Input directory, which we'll modify to be an absolute path without a trailing slash (how Python wants it)
    path_to_process = common_utils.sanitize_and_validate_directory_path(input_path, logger)

    # Create the top-level dict in which we'll store duplicates. Dict keys at this level are file sizes in bytes
    file_duplicates_dict = {}
    # Initialize counters
    files_seen = last_files_seen = directories_seen = bytes_read = bytes_total = 0
    start_time = last_logger_time = time()

    # https://stackoverflow.com/questions/53123867
    # Process top-down. If we wanted bottom up, we could add topdown=False to the walk() arguments
    # dir_path will update to the directory we're currently scanning. It is an absolute path
    # dirs is a list of subdirectories in the current dir_path
    # files is a list of file names in the current dir_path
    for dir_path, dirs, files in walk(path_to_process):
        directories_seen += 1
        # Iterate through files that are immediate children in the current dir_path
        for file in files:
            # Log an update if we haven't logged for a while, going either by time or number of files
            # TODO make this customizable
            current_time = time()
            if (current_time - last_logger_time) > 1 or (files_seen - last_files_seen) > 1000:
                log_current_progress(logger, start_time, current_time, bytes_read, files_seen, directories_seen)
                last_logger_time = current_time
                last_files_seen = files_seen
            files_seen += 1
            # Construct the absolute path that we'll need to access the file
            absolute_file_path = path.join(dir_path, file)
            # Construct the relative path based on user input that we'll end up storing in the dict
            # https://stackoverflow.com/questions/1192978
            input_file_path = path.relpath(absolute_file_path)
            # Get the size of the file, in Bytes
            # https://stackoverflow.com/questions/6591931
            file_size_bytes = path.getsize(absolute_file_path)
            bytes_total += file_size_bytes
            # If we plan to diff on more than just the number of bytes in the file, proceed
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
                                                                                enable_multithreading,
                                                                                disable_full_hashing)
                else:
                    # An entry already existed as the value, so pass it to the helper to update
                    file_duplicates_dict[file_size_bytes] = update_partial_dict(file_duplicates_dict[file_size_bytes],
                                                                                absolute_file_path, input_file_path,
                                                                                file_size_bytes, byte_count_to_hash,
                                                                                enable_multithreading,
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
            "By partially/fully disabling hashing, we skipped reading {:.1f}MB from disk".format(bytes_saved_mb))
        if disable_full_hashing:
            logger.warning("Partial hashing is enabled but still being stored in field full_hash. BE CAREFUL!")
    # Return the dict to the caller
    return file_duplicates_dict


# Provided with the dict computed earlier, parse it into a flattened DataFrame for analysis
def flatten_dict_to_data_frame(file_duplicates_dict):
    # Define a list which will contain the flattened rows to write
    # Schema: file_path::string, full_hash::string, file_size_bytes::int
    # TODO add modified date, hashing date?
    output_list = []

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
                            output_list.append([list_item, level_two_key, level_zero_key])
                else:
                    # If the value wasn't a dict, then it's a list of files.
                    # This occurs when the partial hash was actually a full hash due to the file being small
                    for list_item in level_one_value:
                        output_list.append([list_item, level_one_key[0], level_zero_key])
        else:
            # if the value wasn't a dict, then it's a list of files
            for list_item in level_zero_value:
                output_list.append([list_item, "not_computed", level_zero_key])

    # Now that we have a flat-formatted output_list, input it into a DataFrame while specifying column names
    # https://stackoverflow.com/questions/13784192
    data_frame = pandas.DataFrame(output_list, columns=["relative_path", "hash", "file_size_bytes"])
    return data_frame
