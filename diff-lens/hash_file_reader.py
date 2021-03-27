import pandas


def read_hashes_from_file(input_path):
    # Use pandas to read a TSV file and parse it into a dataFrame
    # https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
    data_frame = pandas.read_csv(input_path, sep="\t", doublequote=False, escapechar="\\", index_col=False)
    pandas.set_option('display.max_rows', None)
    pandas.set_option('display.max_columns', None)
    pandas.set_option('display.width', None)
    pandas.set_option('display.max_colwidth', None)
    data_frame_value_counts = data_frame["full_hash"].value_counts()
    print(data_frame[data_frame["full_hash"].isin(data_frame_value_counts.index[data_frame_value_counts.gt(1)])])
    return data_frame


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # dict_to_write = compute_diffs("../../../../TestDir/")
    new_data_frame = read_hashes_from_file("output.tsv.gz")
