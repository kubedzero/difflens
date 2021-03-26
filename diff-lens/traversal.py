import os
from blake3 import blake3


def update1MDict(dict, filePath):
    with open(filePath, "rb") as f:
        # Modify with read(500000) to read the first 500k bytes
        hash = blake3(f.read()).hexdigest()
        if hash not in dict:
            dict[hash]=[]
        dict[hash].append(filePath)
    return dict

def processBegin():
    # input directory, with or without trailing slash
    inputDirectory = "/absolute/path"

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
                fileBytesDict[fileSizeBytes]=update1MDict({},absoluteFilePath)

            else:
                # An entry already existed, so add this new filePath to the list
                fileBytesDict[fileSizeBytes]=update1MDict(fileBytesDict[fileSizeBytes], absoluteFilePath)

        # We've exited the for loop for the current dirpath, onto the next one


    print(fileBytesDict)


if __name__ == '__main__':
    processBegin()