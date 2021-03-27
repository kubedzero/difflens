import os
from csv import QUOTE_NONNUMERIC

import pandas
import psutil

from compute_diffs import compute_diffs


def print_memory():
    print(psutil.virtual_memory())
    print(psutil.swap_memory())
    # https://stackoverflow.com/questions/938733/total-memory-used-by-python-process
    process = psutil.Process(os.getpid())
    print("MB used by Python process: {}".format(process.memory_info().rss / 1000 / 1000))


def write_hashes_to_file(dict_input, output_path):
    # Define a list which will contain the flattened rows to write
    # Schema: full_hash::string, file_path::string, file_size_bytes::int
    # TODO add modified date, hashing date?
    output_list = []

    # Flatten the data by iterating through the nested dicts in the correct way
    for level_zero_key, level_zero_value in dict_input.items():
        if isinstance(level_zero_value, dict):
            for level_one_key, level_one_value in level_zero_value.items():
                if isinstance(level_one_value, dict):
                    for level_two_key, level_two_value in level_one_value.items():
                        # we should only have 3 levels of dict. At this level, there should be a list as the value
                        for list_item in level_two_value:
                            output_list.append([level_two_key, list_item, level_zero_key])
                else:
                    # If the value wasn't a dict, then it's a list of files
                    for list_item in level_one_value:
                        output_list.append([level_one_key[0], list_item, level_zero_key])
        else:
            # if the value wasn't a dict, then it's a list of files
            for list_item in level_zero_value:
                output_list.append(["not_computed", list_item, level_zero_key])

    # Now that we have a flattened output_list, input it into a DataFrame
    # https://stackoverflow.com/questions/13784192/creating-an-empty-pandas-dataframe-then-filling-it
    # TODO is pandas really needed for this? Only if we do more advanced analysis I think
    data_frame = pandas.DataFrame(output_list, columns=["full_hash", "relative_path", "file_size_bytes"])
    # Get the sum of the number of bytes of all files we read
    print("Total MB of files read: {}".format(data_frame["file_size_bytes"].sum() / 1000 / 1000))

    # https://thispointer.com/python-pandas-how-to-display-full-dataframe-i-e-print-all-rows-columns-without-truncation/
    pandas.set_option('display.max_rows', None)
    pandas.set_option('display.max_columns', None)
    pandas.set_option('display.width', None)
    pandas.set_option('display.max_colwidth', None)
    # print(data_frame.merge(right=data_frame,left_on="full_hash", right_on="full_hash"))

    print_memory()
    # TODO: alternatively, write it using JSON?
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
    data_frame.to_csv(output_path, sep=",", quoting=QUOTE_NONNUMERIC, doublequote=False, escapechar="\\", index=False)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    dict_to_write = compute_diffs("../../../../TestDir/")
    write_hashes_to_file(dict_to_write, "output.tsv.gz")
