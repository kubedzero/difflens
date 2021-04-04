from .loghelper import get_logger_with_name


def sanitize_and_dedupe_extension_list(list_to_process):
    # Create a set that guarantees unique entries
    output_set = set()
    if list_to_process is not None:
        for extension_string in list_to_process:
            if extension_string.startswith("*"):
                # Remove the leading * if it exists, leaving hopefully .ext
                # https://stackoverflow.com/questions/4945548
                extension_string = extension_string[1:]
            output_set.add(extension_string)
    return list(output_set)


def sanitize_and_dedupe_path_list(list_to_process):
    # Create a set that guarantees unique entries
    output_set = set()
    if list_to_process is not None:
        for path_string in list_to_process:
            # Remove the leading ./ or . if it exists, leaving hopefully dir/dir/
            if path_string.startswith("./"):
                # https://stackoverflow.com/questions/4945548
                path_string = path_string[2:]
            elif path_string.startswith("."):
                # https://stackoverflow.com/questions/4945548
                path_string = path_string[1:]
            # Remove the trailing / if it exists, leaving hopefully dir/dir
            if path_string.endswith("/"):
                # https://stackoverflow.com/questions/15478127
                path_string = path_string[:-1]
            output_set.add(path_string)
    return list(output_set)


class PathExcluder:
    def __init__(self, extension_exclude_list, path_exclude_list, log_level):
        self.logger = get_logger_with_name("PathExcluder", log_level)
        self.extension_exclude_list = sanitize_and_dedupe_extension_list(extension_exclude_list)
        self.path_exclude_list = sanitize_and_dedupe_path_list(path_exclude_list)
        self.logger.info("PathExcluder initialized with excluded dirs {} and excluded extensions {}".format(
            self.path_exclude_list, self.extension_exclude_list))

    def is_excluded_dir(self, input_path):
        for path in self.path_exclude_list:
            if input_path.startswith(path):
                self.logger.info("Directory {} matched exclusion rule, skipping".format(input_path))
                return True
        return False

    def has_excluded_extension(self, file_name):
        for extension in self.extension_exclude_list:
            if file_name.endswith(extension):
                self.logger.debug("File {} matched exclusion rule {}, skipping".format(file_name, extension))
                return True
        return False
