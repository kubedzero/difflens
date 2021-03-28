# This is the entry to the project, what a CLI user of python will call
from os import chdir

import pandas

from common_utils import print_memory
from compare_files import determine_duplicate_files, determine_modified_files, determine_removed_files
from compute_diffs import compute_diffs, flatten_dict_to_data_frame
from hash_file_io import write_hashes_to_file, read_hashes_from_file

if __name__ == '__main__':
    # Configure printing options so the full data_frame prints
    pandas.set_option('display.max_rows', None)
    pandas.set_option('display.max_columns', None)
    pandas.set_option('display.width', None)
    pandas.set_option('display.max_colwidth', None)

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
    print("old output equals read?", output_data_frame.equals(input_old))
    print("new output equals read?", output_data_frame_new.equals(input_new))
    # Todo determine processing speed by taking MB/time during hashing, files/time for hashing, files/time for comparing

    print_memory()
    # Get the sum of the number of bytes of all files we read
    print("Total MB of files read: {}".format(input_new["file_size_bytes"].sum() / 1000 / 1000))

    print("find deleted files")
    deleted_data_frame = determine_removed_files(input_old, input_new)
    print(deleted_data_frame)

    print("find added files")
    added_data_frame = determine_removed_files(input_new, input_old)
    print(added_data_frame)

    print("find modified files")
    modified_data_frame = determine_modified_files(input_old, input_new)
    print(modified_data_frame)

    print("find duplicate files")
    duplicates_data_frame = determine_duplicate_files(input_new)
    print(duplicates_data_frame)
