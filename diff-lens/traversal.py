import os

from blake3 import blake3


# https://stackoverflow.com/questions/3229419/how-to-pretty-print-nested-dictionaries
def pretty(d, indent=2):
    for key, value in d.items():
        print(' ' * indent + str(key))
        if isinstance(value, dict):
            pretty(value, indent + 1)
        else:
            print(' ' * (indent + 1) + str(value))


def updateFullHashDict(dict, absolutePath, relativePath):
    with open(absolutePath, "rb") as f:
        # Modify with read(500000) to read the first 500k bytes
        # Confirmed that the read() input matches the units of os.path.getsize()
        # As suggested in https://github.com/oconnor663/blake3-py enable multiThreading if file >=1MB
        # TODO make multithreading an input param or flag
        hash = blake3(f.read(), multithreading=True).hexdigest()

        # TODO add a blocker noting whether or not there are more bytes in the file
        if hash not in dict:
            dict[hash] = [relativePath]
        else:
            dict[hash].append(relativePath)

    return dict


def updatePartialDict(dict, absolutePath, relativePath, fileSizeBytes):
    with open(absolutePath, "rb") as f:
        # TODO make the partial hash cutoff an input param or a flag
        hashByteCount = 1000000
        # Modify with read(500000) to read the first 500k bytes
        # Confirmed that the read() input matches the units of os.path.getsize()
        hash = blake3(f.read(hashByteCount)).hexdigest()

        # Make the dictKey a tuple indicating the hash value, but also a Boolean on whether or not the file was smaller than the read buffer.
        # If true, we don't need additional hashing since we already covered the full file. If false, continue hashing
        fileFullyHashed = fileSizeBytes <= hashByteCount
        dictKey = (hash, fileFullyHashed)

        if not fileFullyHashed:
            # TODO add a blocker noting whether or not there are more bytes in the file
            if dictKey not in dict:
                dict[dictKey] = updateFullHashDict({}, absolutePath, relativePath)
            else:
                dict[dictKey] = updateFullHashDict(dict[dictKey], absolutePath, relativePath)
        else:
            if dictKey not in dict:
                dict[dictKey] = [relativePath]
            else:
                dict[dictKey].append(relativePath)

    return dict


def processBegin():
    # raw argument
    inputPath = "../../../../TestDir/innerDir/"
    # input directory, with or without trailing slash, may be absolute or relative
    pathToProcess = inputPath

    # Check if the input is a relative or absolute path
    # https://automatetheboringstuff.com/chapter8/
    if os.path.isabs(pathToProcess):
        print("Input path was absolute, not modifying")
    else:
        if pathToProcess.startswith("~"):
            print("Input path contained a tilde, performing user expansion")
            pathToProcess = os.path.expanduser(pathToProcess)
        else:
            print("Input path was relative, converting it to absolute path")
            pathToProcess = os.path.abspath(pathToProcess)
    print("Proceeding processing with path {} from current working directory {}".format(pathToProcess, os.getcwd()))

    # top-level dict. Key is file bytes. Value is another dict
    fileBytesDict = {}

    # must be a directory.
    # TODO: may not work with relative paths
    if not os.path.isdir(pathToProcess):
        print("Input wasn't a directory, exiting")
        exit(1)
    else:
        print("Input confirmed to be a valid directory")

    # get last character and remove trailing slash if necessary to standardize with os.walk() subdirectories
    if pathToProcess[-1] == os.sep:
        print("Last character of directory is a slash, removing it")
        pathToProcess = pathToProcess[:-1]
    else:
        print("Input path correctly ended without a trailing slash")

    # https://stackoverflow.com/questions/53123867/renaming-folders-and-files-while-os-walking-them-missed-some-files-after-chang
    # Process top-down. If we wanted bottom up, we could add topdown=False to the os.walk() arguments
    # dirpath will update to the directory we're currently scanning.
    # dirs is a list of subdirectories in the current dirpath
    # files is a list of file names in the current dirpath
    for dirpath, dirs, files in os.walk(pathToProcess):
        # iterate through files that are immediate children in the current dirpath
        for file in files:
            # construct the absolute path that we'll need to access the file
            absoluteFilePath = os.path.join(dirpath, file)
            # Construct the relative path based on user input that we'll end up storing
            inputFilePath = os.path.join(inputPath, file)
            # get the size of the file, in Bytes
            # https://stackoverflow.com/questions/6591931/getting-file-size-in-python
            fileSizeBytes = os.path.getsize(absoluteFilePath)
            # Check if the fileBytesDict already contains an entry for the current file's size
            if fileSizeBytes not in fileBytesDict:
                # If no entry existed, create a new list containing our filename
                fileBytesDict[fileSizeBytes] = updatePartialDict({}, absoluteFilePath, inputFilePath, fileSizeBytes)

            else:
                # An entry already existed, so add this new filePath to the list
                fileBytesDict[fileSizeBytes] = updatePartialDict(fileBytesDict[fileSizeBytes], absoluteFilePath,
                                                                 inputFilePath,
                                                                 fileSizeBytes)

        # We've exited the for loop for the current dirpath, onto the next one

    pretty(fileBytesDict)


# TODO get this all wrapped into a function where all customizations are given as input args. then return the assembled dict
# TODO a separate file will handle writing the dict in the proper format into a file
# TODO a separate file will handle diffing one file with another to determine changes. It'll have different modes for presence/absence (reverse the inputs!), hash comparison, etc

if __name__ == '__main__':
    processBegin()
