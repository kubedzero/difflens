import os

from compute_diffs import compute_diffs
from hash_file_reader import read_hashes_from_file
from hash_file_writer import write_hashes_to_file


def determine_removed_files(original_data_frame, comparator_data_frame):
    # todo left join? and when join field is null on right
    # for each filename in the old data frame
    # check if the new dataframe contains the same file (aka in the same path)
    # if the file exists in the new dataframe,
    # bonus: check if the hashes are the same, and print out if they aren't
    # otherwise, add the file to the list of deleted files
    # https://pandas.pydata.org/docs/user_guide/merging.html#database-style-dataframe-or-named-series-joining-merging
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html
    print("removed")
    analysis_data_frame = original_data_frame.merge(comparator_data_frame, how="left", on="relative_path",
                                                    validate="one_to_one")
    # Filter the merged dataframe to only include files that were not present in the comparator data_frame
    # Thanks to left outer join, the fields merged from the comparator will be NaN if the filename wasn't present there
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.isna.html#pandas.DataFrame.isna
    filtered_data_frame = analysis_data_frame[analysis_data_frame["full_hash_y"].isna()]
    print(filtered_data_frame)


def determine_added_files(old_data_frame, new_data_frame):
    # Reuse the removed_files dataframe with the inputs swapped, since it's the same
    print("added")


def determine_modified_files(old_data_frame, new_data_frame):
    # join the old and the new dataframe on the filename. Inner join if possible
    # iterate through the remaining rows, which exist in both old and new
    # check the old hash versus the new hash and ensure they are the same
    print("hello")


def determine_duplicate_files(old_data_frame, new_data_frame):
    # honestly, going through the dict might be easier
    # Otherwise use the hack we had in the other file to parse down the dataframe
    # todo what does duplicate mean in the context of an old and a new? No diff necessary
    # todo benchmark dataframe traversal vs dict traversal
    # https://pandas.pydata.org/docs/user_guide/merging.html#database-style-dataframe-or-named-series-joining-merging
    print("hello")


def compare_hash_data_frames(old_data_frame, new_data_frame, mode):
    if mode == "removed_files":
        print("removed")
    elif mode == "added_files":
        print("added")
    elif mode == "changed_files":
        print("changed")
    else:
        print("hi")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # https://www.geeksforgeeks.org/python-os-chdir-method/
    os.chdir("/Users/kz/TestDir")
    dict_to_write = compute_diffs(".")
    os.chdir("/Users/kz/TestDir 2")
    dict_to_write_new = compute_diffs(".")

    write_hashes_to_file(dict_to_write, "old.tsv.gz")
    write_hashes_to_file(dict_to_write_new, "new.tsv.gz")

    old_data_frame = read_hashes_from_file("old.tsv.gz")
    new_data_frame = read_hashes_from_file("new.tsv.gz")

    determine_added_files(old_data_frame, new_data_frame)
    determine_removed_files(old_data_frame, new_data_frame)
    # TODO split out dict to dataframe creation
    # Todo determine processing speed by taking MB/time during hashing, files/time for hashing, files/time for comparing
    # TODO run through scenarios of diffing dataframes vs diffs
