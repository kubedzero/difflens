# Return a list of files that existed in the original data frame but not in the comparison data frame
# Run determine_removed_files(old, new) to find removed files and determine_removed_files(new, old) to find added files
def determine_removed_files(original_data_frame, comparison_data_frame):
    # Join the comparison onto the original based on relative path
    # Use a left join to preserve all original rows. If the comparison couldn't join, its fields for that row are NaN
    # Validate that each relative path is unique across all rows in each input data_frame
    # https://pandas.pydata.org/docs/user_guide/merging.html#database-style-dataframe-or-named-series-joining-merging
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html
    analysis_data_frame = original_data_frame.merge(comparison_data_frame, how="left", on="relative_path",
                                                    validate="one_to_one")
    # Filter the merged dataframe to only include files that were not present in the comparison data_frame
    # Thanks to left outer join, the fields merged from the comparison will be NaN if the filename wasn't present there
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.isna.html#pandas.DataFrame.isna
    filtered_data_frame = analysis_data_frame[analysis_data_frame["hash_y"].isna()]
    # Reduce the filtered data frame to only fields we care about: filename, hash, and size in bytes
    # https://www.analyseup.com/python-data-science-reference/pandas-selecting-dropping-and-renaming-columns.html
    reduced_data_frame = filtered_data_frame[["relative_path", "hash_x", "file_size_bytes_x"]]
    # Rename the reduced data frame to have friendly column names, discarding the merge artifacts
    reduced_data_frame.columns = ["relative_path", "hash", "file_size_bytes"]
    return reduced_data_frame


# Return a list of files that had a hash change between the original and comparison data_frame
def determine_modified_files(original_data_frame, comparison_data_frame):
    # Join the comparison onto the original based on relative path
    # Use an inner join to preserve only rows with a relative path that exists in both the original and comparison
    # This ensures that the hash for that file exists in both the original and comparison
    # Validate that each relative path is unique across all rows in each input data_frame
    analysis_data_frame = original_data_frame.merge(comparison_data_frame, how="inner", on="relative_path",
                                                    validate="one_to_one")
    # Next, filter the data_frame to only contain rows where the original and comparison hash differ
    filtered_data_frame = analysis_data_frame[analysis_data_frame["hash_x"] != analysis_data_frame["hash_y"]]
    # Reduce the filtered data frame to only fields we care about: filename
    # TODO maybe use modification_date here to determine corruption, aka hash changes without modification_date change
    # https://www.analyseup.com/python-data-science-reference/pandas-selecting-dropping-and-renaming-columns.html
    reduced_data_frame = filtered_data_frame["relative_path"]
    return reduced_data_frame


# Return a list of files sharing a duplicate field (hash or size) with at least one other file having a different path
def determine_duplicate_files(data_frame, duplicate_field):
    # Create a Series containing all the unique values in the hash field, and the count of each
    # https://stackoverflow.com/questions/48628417
    # https://pandas.pydata.org/docs/reference/api/pandas.Series.value_counts.html
    data_frame_value_counts = data_frame[duplicate_field].value_counts()
    # Filter to an Index of hashes that appeared more than once in the data_frame
    multiple_occurrence_hashes = data_frame_value_counts.index[data_frame_value_counts.gt(1)]
    # Filter the data_frame to only include rows whose hash appeared in the multiple_occurrence_hashes Index
    filtered_data_frame = data_frame[
        data_frame[duplicate_field].isin(multiple_occurrence_hashes)]
    # Reduce the data_frame to only the fields we care about: hash and filename
    reduced_data_frame = filtered_data_frame[[duplicate_field, "relative_path"]]
    return reduced_data_frame
