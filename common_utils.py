from os import path, sep, getpid

import psutil


def print_memory():
    print(psutil.virtual_memory())
    print(psutil.swap_memory())
    # https://stackoverflow.com/questions/938733
    process = psutil.Process(getpid())
    print("MB used by Python process: {}".format(process.memory_info().rss / 1000 / 1000))


def resolve_absolute_path(path_to_process):
    # Check if the input is a relative or absolute path
    # https://automatetheboringstuff.com/chapter8/
    if not path.isabs(path_to_process):
        # Check if the input was not just relative, but also needed user expansion
        # https://stackoverflow.com/questions/2057045
        # https://www.geeksforgeeks.org/python-os-path-expanduser-method/
        if path_to_process.startswith("~"):
            print("Input path {} contained a tilde, performing user expansion".format(path_to_process))
            path_to_process = path.expanduser(path_to_process)
        else:
            print("Input path {} was relative, converting it to absolute path".format(path_to_process))
            path_to_process = path.abspath(path_to_process)
    print("Continuing with absolute path {}".format(path_to_process))
    return path_to_process


def sanitize_and_validate_file_path(path_to_process):
    # Update the input path to be absolute
    path_to_process = resolve_absolute_path(path_to_process)
    # Now that we have an absolute path, confirm it does not point at a directory and exit early if so
    if path.isdir(path_to_process):
        print("Path points to a directory, but a file is needed. Exiting")
        exit(1)
    return path_to_process


def sanitize_and_validate_directory_path(path_to_process):
    # Update the input path to be absolute
    path_to_process = resolve_absolute_path(path_to_process)
    # Now that we have an absolute path, confirm it points to a directory and not a file
    if not path.isdir(path_to_process):
        print("Input wasn't a directory, exiting")
        exit(1)

    # Clear the path of a trailing slash if one exists, to standardize with walk() subdirectories
    if path_to_process[-1] == sep:
        print("Last character of directory is a slash, removing it")
        path_to_process = path_to_process[:-1]
    else:
        print("Input path correctly ended without a trailing slash")
    return path_to_process
