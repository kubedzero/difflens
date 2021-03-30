# Used to set the output mode when writing tabular data
from csv import QUOTE_NONNUMERIC

# Used to read tabular data from a file on disk
from pandas import read_csv

from common_utils import sanitize_and_validate_file_path


# TODO make a utility that concatenates inputs on relative path, hopefully validating that there are no duplicates
# Intended for merging the data_frames of multiple disks into one to store or diff
# A validation error would indicate two disks have the same file, and in that case which will Unraid use?

# Rename data_frame input column "hash" to "full_hash" or "partial_hash" based on the disable_full_hashing flag
# Alternatively, perform the reverse operation, standardizing "full_hash" or "partial_hash" to "hash"
def update_data_frame_hash_column_name(data_frame, disable_full_hashing, logger, prepare_for_writing):
    if disable_full_hashing:
        column_name = "partial_hash"
    else:
        column_name = "full_hash"

    if prepare_for_writing:
        logger.debug("Renaming column 'hash' to '{}' before writing to disk".format(column_name))
        return data_frame.rename(columns={"hash": column_name}, inplace=False)
    else:
        # Prevent accessing a column that does not exist by checking before renaming
        # https://stackoverflow.com/questions/24870306
        if column_name in data_frame.columns:
            logger.debug("Renaming column {} to 'hash' after reading from disk".format(column_name))
            # https://stackoverflow.com/questions/11346283
            return data_frame.rename(columns={column_name: "hash"}, inplace=True)
        else:
            message = "Column '{}' did not exist in the input! Did you switch between partial and full hashing?".format(
                column_name)
            logger.error(message)
            # https://docs.python.org/3/library/exceptions.html
            # https://www.w3schools.com/python/gloss_python_raise.asp
            raise ValueError(message)


def read_hashes_from_file(input_path, logger, disable_full_hashing):
    # Pandas can handle relative paths, but handle relative->absolute conversion here so extra info can print
    input_path = sanitize_and_validate_file_path(input_path, logger)
    # Use pandas to read a TSV file and parse it into a dataFrame
    # https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
    # Use tabs as separators
    # Don't allow double-quotes inside fields without escaping
    # Use a backslash \ character to escape separators or double quotes inside fields
    # Don't read the first field in each row as the row index
    data_frame = read_csv(input_path, sep="\t", doublequote=False, escapechar="\\", index_col=False)
    update_data_frame_hash_column_name(data_frame, disable_full_hashing, logger, prepare_for_writing=False)
    return data_frame


def write_hashes_to_file(data_frame, output_path, logger, disable_full_hashing=False, hash_column_exists=True):
    # Only try updating the hash column if the caller indicated it was present in the data_frame
    if hash_column_exists:
        data_frame = update_data_frame_hash_column_name(data_frame, disable_full_hashing, logger,
                                                        prepare_for_writing=True)
    # Pandas can handle relative paths, but handle relative->absolute conversion here so extra info can print
    output_path = sanitize_and_validate_file_path(output_path, logger)
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
    # Use tabs as separators
    # double-quote around all non-numeric fields, just to keep things standardized
    # Don't allow double-quotes inside fields without escaping
    # Use a backslash \ character to escape separators or double quotes inside fields
    # Don't prepend a field containing the row index
    data_frame.to_csv(output_path, sep="\t", quoting=QUOTE_NONNUMERIC, doublequote=False, escapechar="\\", index=False)
