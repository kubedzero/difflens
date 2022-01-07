# Used to set the output mode when writing tabular data
from csv import QUOTE_NONNUMERIC

# Used to read tabular data from a file on disk
from pandas import read_csv, concat

from difflens.util.commonutils import sanitize_and_validate_file_path
from difflens.util.compareMode import CompareMode


# Rename data_frame input column "hash" to the compare_mode in preparation for writing to disk
# Alternatively, standardize the data_frame read from disk by renaming the compare_mode column to "hash"
# NOTE: The "size" column is always present and thus renaming
def update_data_frame_hash_column_name(data_frame, original_column_name, new_column_name, logger, in_place_flag):
    # Prevent accessing a column that does not exist by checking before renaming
    # https://stackoverflow.com/questions/24870306
    if original_column_name in data_frame.columns:
        logger.debug("Renaming column {} to '{}' with inPlace value of {}".format(original_column_name,
                                                                                  new_column_name, in_place_flag))
        # Since inplace=True will not return an object, we have to call and then return the input
        if in_place_flag:
            data_frame.rename(columns={original_column_name: new_column_name}, inplace=True)
            return data_frame
        else:
            # Otherwise inplace=False and a new object is returned from the rename that we can then return
            return data_frame.rename(columns={original_column_name: new_column_name}, inplace=False)
    else:
        message = "Column '{}' did not exist in the input! Did you switch between partial and full hashing?".format(
            original_column_name)
        logger.error(message)
        # https://docs.python.org/3/library/exceptions.html
        # https://www.w3schools.com/python/gloss_python_raise.asp
        raise ValueError(message)


# Given a list of input paths pointing to tabular data files, read each and return their DataFrame concatenation
def read_hashes_from_files(input_paths, logger, compare_mode):
    data_frame_list = []
    for path in input_paths:
        # Pandas can read relative paths, but handle relative->absolute conversion here so extra info can print
        path = sanitize_and_validate_file_path(path, logger)
        # Use pandas to read a TSV file and parse it into a dataFrame
        # https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
        # Use tabs as separators
        # Don't allow double-quotes inside fields without escaping
        # Use a backslash \ character to escape separators or double quotes inside fields
        # Don't read the first field in each row as the row index
        data_frame = read_csv(path, sep="\t", doublequote=False, escapechar="\\", index_col=False)
        # Standardize the hash mode column to "hash" even if the compare_mode is SIZE, to make modified/duplicate
        # comparison simpler since whatever the compare_mode, it will be in the same column
        # NOTE: Since the compare_mode has dashes but the file uses underscores, replace the character
        data_frame = update_data_frame_hash_column_name(data_frame, compare_mode.replace("-", "_"), "hash", logger,
                                                        True)
        data_frame_list.append(data_frame)
    # Now that all the input paths have been read in as DataFrames, concatenate them into one DataFrame and return
    concat_data_frame = concat(data_frame_list)
    return concat_data_frame


# Given a data_frame and a compare_mode, update the "hash" column to the proper compare_mode name
# and write the data_frame to disk
def write_hashes_to_file(data_frame, output_path, logger, compare_mode):
    # If not in SIZE mode and the "hash" column exists in the data_frame, rename it with the proper compare_mode
    # Do not update the data_frame in place as we may modify it or use it later and want it in its original state
    # NOTE: Since the compare_mode has dashes but the file uses underscores, replace the character
    if "hash" in data_frame.columns and not compare_mode == CompareMode.SIZE.value:
        data_frame = update_data_frame_hash_column_name(data_frame, "hash", compare_mode.replace("-", "_"), logger,
                                                        False)
    # Pandas can handle relative paths, but handle relative->absolute conversion here so extra info can print
    output_path = sanitize_and_validate_file_path(output_path, logger)
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
    # Use tabs as separators
    # double-quote around all non-numeric fields, just to keep things standardized
    # Don't allow double-quotes inside fields without escaping
    # Use a backslash \ character to escape separators or double quotes inside fields
    # Don't prepend a field containing the row index
    data_frame.to_csv(output_path, sep="\t", quoting=QUOTE_NONNUMERIC, doublequote=False, escapechar="\\", index=False)
