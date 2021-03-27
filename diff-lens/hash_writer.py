import csv

from compute_diffs import compute_diffs


def write_hashes_to_file(dict_input):
    with open("output.csv", "w", newline='') as csv_file:
        fieldnames = ["full_hash", "file_path", "file_size_bytes"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for level_zero_key, level_zero_value in dict_input.items():
            if isinstance(level_zero_value, dict):
                for level_one_key, level_one_value in level_zero_value.items():
                    if isinstance(level_one_value, dict):
                        for level_two_key, level_two_value in level_one_value.items():
                            # we should only have 3 levels of dict. At this level, there should be a list as the value
                            for list_item in level_two_value:
                                writer.writerow({"full_hash": level_two_key, "file_path": list_item,
                                                 "file_size_bytes": level_zero_key})
                    else:
                        # If the value wasn't a dict, then it's a list of files
                        for list_item in level_one_value:
                            writer.writerow(
                                {"full_hash": level_one_key[0], "file_path": list_item,
                                 "file_size_bytes": level_zero_key})
            else:
                # if the value wasn't a dict, then it's a list of files
                for list_item in level_zero_value:
                    writer.writerow(
                        {"full_hash": "not_computed", "file_path": list_item, "file_size_bytes": level_zero_key})


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    dict_to_write = compute_diffs("../../../../TestDir/innerDir/")
    write_hashes_to_file(dict_to_write)
