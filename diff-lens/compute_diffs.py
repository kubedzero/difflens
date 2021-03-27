from os import path, sep, walk, getcwd

from blake3 import blake3


# Helper to handle creating or updating a list stored in a dict
def add_or_update_dict_list(dict_to_update, dict_key, string_to_store):
    if dict_key not in dict_to_update:
        dict_to_update[dict_key] = [string_to_store]
    else:
        dict_to_update[dict_key].append(string_to_store)
    return dict_to_update


# Helper that can pretty print a nested dict
# https://stackoverflow.com/questions/3229419/how-to-pretty-print-nested-dictionaries
def pretty(d, indent=2):
    for key, value in d.items():
        print(' ' * indent + str(key))
        if isinstance(value, dict):
            pretty(value, indent * 2)
        else:
            print(' ' * (indent + 1) + str(value))


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
                        enable_multithreading, enable_full_hash):
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
            if enable_full_hash:
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


# enableMultithreading is True by default because we assume files being hashed are >1MB and therefore
# most efficiently hashed in a multi-threaded manner.
def compute_diffs(input_path, byte_count_to_hash=1000000, enable_multithreading=True, enable_partial_hash=True,
                  enable_full_hash=True):
    # Input directory, which we'll modify to be an absolute path without a trailing slash (how Python wants it)
    path_to_process = input_path

    # Check if the input is a relative or absolute path
    # https://automatetheboringstuff.com/chapter8/
    if path.isabs(path_to_process):
        print("Input path was absolute, not modifying")
    else:
        # Check if the input was not just relative, but also needed user expansion
        # https://stackoverflow.com/questions/2057045/pythons-os-makedirs-doesnt-understand-in-my-path
        # https://www.geeksforgeeks.org/python-os-path-expanduser-method/
        if path_to_process.startswith("~"):
            print("Input path contained a tilde, performing user expansion")
            path_to_process = path.expanduser(path_to_process)
        else:
            print("Input path was relative, converting it to absolute path")
            path_to_process = path.abspath(path_to_process)
    print("Proceeding processing with path {} from current working directory {}".format(path_to_process, getcwd()))

    # Now that we have an absolute path, confirm it points to a directory and not a file
    if not path.isdir(path_to_process):
        print("Input wasn't a directory, exiting")
        exit(1)
    else:
        print("Input confirmed to be a valid directory")

    # Clear the path of a trailing slash if one exists, to standardize with walk() subdirectories
    if path_to_process[-1] == sep:
        print("Last character of directory is a slash, removing it")
        path_to_process = path_to_process[:-1]
    else:
        print("Input path correctly ended without a trailing slash")

    # Create the top-level dict in which we'll store duplicates. Dict keys at this level are file sizes in bytes
    file_duplicates_dict = {}

    # https://stackoverflow.com/questions/53123867/renaming-folders-and-files-while-os-walking-them-missed-some-files-after-chang
    # Process top-down. If we wanted bottom up, we could add topdown=False to the walk() arguments
    # dir_path will update to the directory we're currently scanning.
    # dirs is a list of subdirectories in the current dir_path
    # files is a list of file names in the current dir_path
    for dir_path, dirs, files in walk(path_to_process):

        # Iterate through files that are immediate children in the current dir_path
        for file in files:
            # Construct the absolute path that we'll need to access the file
            absolute_file_path = path.join(dir_path, file)
            # Construct the relative path based on user input that we'll end up storing in the dict
            input_file_path = path.join(input_path, file)
            # Get the size of the file, in Bytes
            # https://stackoverflow.com/questions/6591931/getting-file-size-in-python
            file_size_bytes = path.getsize(absolute_file_path)
            # If we plan to diff on more than just the number of bytes in the file, proceed
            if enable_partial_hash:
                # Check if the fileBytesDict already contains an entry for the current file's size
                if file_size_bytes not in file_duplicates_dict:
                    # If no entry existed, create a new dict as a value and populate it using a helper
                    file_duplicates_dict[file_size_bytes] = update_partial_dict({}, absolute_file_path, input_file_path,
                                                                                file_size_bytes, byte_count_to_hash,
                                                                                enable_multithreading, enable_full_hash)
                else:
                    # An entry already existed as the value, so pass it to the helper
                    file_duplicates_dict[file_size_bytes] = update_partial_dict(file_duplicates_dict[file_size_bytes],
                                                                                absolute_file_path, input_file_path,
                                                                                file_size_bytes, byte_count_to_hash,
                                                                                enable_multithreading, enable_full_hash)
            else:
                # Otherwise finish processing this file by adding its bytes to the dict
                file_duplicates_dict = add_or_update_dict_list(file_duplicates_dict, file_size_bytes,
                                                               input_file_path)

    # We've exited the for loop for the current dir_path, onto the next one
    # Return the dict to the caller
    return file_duplicates_dict


# TODO a separate file will handle writing the dict in the proper format into a file
# TODO a separate file will handle diffing one file with another to determine changes.
#  It'll have different modes for presence/absence (reverse the inputs!), hash comparison, etc

if __name__ == '__main__':
    output = compute_diffs("../../../../TestDir/innerDir/")
    # Print out the struct we created
    pretty(output)
