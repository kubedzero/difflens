import os
from blake3 import blake3

# https://stackoverflow.com/questions/3229419/how-to-pretty-print-nested-dictionaries
def pretty(d, indent=0):
   for key, value in d.items():
      print('\t' * indent + str(key))
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
         print('\t' * (indent+1) + str(value))

def updateFullHashDict(dict, filePath):
    with open(filePath, "rb") as f:
        # Modify with read(500000) to read the first 500k bytes
        # Confirmed that the read() input matches the units of os.path.getsize()
        hash = blake3(f.read()).hexdigest()

        # TODO add a blocker noting whether or not there are more bytes in the file
        if hash not in dict:
            dict[hash] = [filePath]
        else:
            dict[hash].append(filePath)

    return dict


def updatePartialDict(dict, filePath, fileSizeBytes):
    with open(filePath, "rb") as f:
        hashByteCount=1000000
        # Modify with read(500000) to read the first 500k bytes
        # Confirmed that the read() input matches the units of os.path.getsize()
        hash = blake3(f.read(hashByteCount)).hexdigest()

        # Make the dictKey a tuple indicating the hash value, but also a Boolean on whether or not the file was smaller than the read buffer.
        # If true, we don't need additional hashing since we already covered the full file. If false, continue hashing
        fileFullyHashed=fileSizeBytes<=hashByteCount
        dictKey = (hash, fileFullyHashed)

        if not fileFullyHashed:
            # TODO add a blocker noting whether or not there are more bytes in the file
            if dictKey not in dict:
                dict[dictKey]=updateFullHashDict({}, filePath)
            else:
                dict[dictKey]=updateFullHashDict(dict[dictKey], filePath)
        else:
            if dictKey not in dict:
                dict[dictKey] = [filePath]
            else:
                dict[dictKey].append(filePath)

    return dict

def processBegin():
    # input directory, with or without trailing slash
    inputDirectory = "/Users/kz/My Games"

    # top-level dict. Key is file bytes. Value is another dict
    fileBytesDict={}

    # must be a directory.
    # TODO: may not work with relative paths
    if not os.path.isdir(inputDirectory):
        print("Input wasn't a directory, exiting")
        exit(1)

    # get last character and remove trailing slash if necessary to standardize with os.walk() subdirectories
    if inputDirectory[-1] == os.sep:
        print("Last character of directory is a slash, removing it")
        inputDirectory = inputDirectory[:-1]

    # https://stackoverflow.com/questions/53123867/renaming-folders-and-files-while-os-walking-them-missed-some-files-after-chang
    # Process top-down. If we wanted bottom up, we could add topdown=False to the os.walk() arguments
    # dirpath will update to the directory we're currently scanning.
    # dirs is a list of subdirectories in the current dirpath
    # files is a list of file names in the current dirpath
    for dirpath, dirs, files in os.walk(inputDirectory):
        # iterate through files that are immediate children in the current dirpath
        for file in files:
            # construct the absolute path that we'll need to access the file
            absoluteFilePath=os.path.join(dirpath,file)
            # get the size of the file, in Bytes
            # https://stackoverflow.com/questions/6591931/getting-file-size-in-python
            fileSizeBytes=os.path.getsize(absoluteFilePath)
            # Check if the fileBytesDict already contains an entry for the current file's size
            if fileSizeBytes not in fileBytesDict:
                # If no entry existed, create a new list containing our filename
                fileBytesDict[fileSizeBytes]=updatePartialDict({}, absoluteFilePath, fileSizeBytes)

            else:
                # An entry already existed, so add this new filePath to the list
                fileBytesDict[fileSizeBytes]=updatePartialDict(fileBytesDict[fileSizeBytes], absoluteFilePath, fileSizeBytes)

        # We've exited the for loop for the current dirpath, onto the next one


    pretty(fileBytesDict)


if __name__ == '__main__':
    processBegin()