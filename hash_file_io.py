from csv import QUOTE_NONNUMERIC

import pandas

import common_utils


def read_hashes_from_file(input_path, logger):
    # Pandas can handle relative paths, but handle relative->absolute conversion ourselves so we can print extra info
    input_path = common_utils.sanitize_and_validate_file_path(input_path, logger)
    # Use pandas to read a TSV file and parse it into a dataFrame
    # https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
    # Use tabs as separators
    # Don't allow double-quotes inside fields without escaping
    # Use a backslash \ character to escape separators or double quotes inside fields
    # Don't read the first field in each row as the row index
    data_frame = pandas.read_csv(input_path, sep="\t", doublequote=False, escapechar="\\", index_col=False)
    return data_frame


def write_hashes_to_file(data_frame, output_path, logger):
    # Pandas can handle relative paths, but handle relative->absolute conversion ourselves so we can print extra info
    output_path = common_utils.sanitize_and_validate_file_path(output_path, logger)
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
    # Use tabs as separators
    # double-quote around all non-numeric fields, just to keep things standardized
    # Don't allow double-quotes inside fields without escaping
    # Use a backslash \ character to escape separators or double quotes inside fields
    # Don't prepend a field containing the row index
    data_frame.to_csv(output_path, sep="\t", quoting=QUOTE_NONNUMERIC, doublequote=False, escapechar="\\", index=False)
