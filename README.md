# DiffLens

## Overview
DiffLens (or difflens) is a package to compute, export, and analyze BLAKE3 file hashes and directory structures. Provided with a directory input, it will scan for files under that directory and compute BLAKE3 hashes based on their contents. If reading the entire file is too slow, options are provided for reading only the first 1 megabyte of each file, or even to treat the file size as the "hash." Once the directory is scanned and these hashes are computed, an option is given to output the aggregated set of hashes to disk.

This is where things start to get interesting. DiffLens can optionally read in a set of hashes from a previous scan and then compare it to the new hashes. This enables a user of DiffLens to identify files that have changed their contents since the last scan, as well as see which files have been added or deleted when compared to the last scan. Even if a comparison set of hashes isn't passed in, DiffLens can still do some analysis on only the files it just scanned, such as looking for files with duplicate content. 

## More Information

This project's hashing is powered by [BLAKE3](https://github.com/BLAKE3-team/BLAKE3), the successor to [BLAKE2/2b/2s](https://www.blake2.net/). BLAKE3 promises to be "much faster than MD5, SHA-1, SHA-2, SHA-3, and BLAKE2" so the bottleneck for DiskLens is most probably a disk's I/O rather than a CPU. 

This project's analysis is powered by [pandas](https://pandas.pydata.org/), an industry-standard data manipulation and analysis library. Once the BLAKE3 hashes are computed, they're loaded into pandas DataFrames to run all the analysis mentioned above, and then output to disk in tabular format

## Unraid & `runDiffLens.sh`

Inspiration for DiffLens came from Bergware's [File Integrity](https://github.com/bergware/dynamix/tree/master/source/file-integrity) plugin for the Unraid NAS OS. It was used for weekly scans of all disks in the array to catch any [bit rot](https://en.wikipedia.org/wiki/Data_degradation) causing corrupted or inaccessible files on the array. Some functionality was lacking however, such as re-analysis of old executions, false positives due to non-Linux OSs updating files via network protocols such as Samba(SMB), and easy inspection of performance. Furthermore, File Integrity does not have BLAKE3 as a hashing option, and stores hashes in the [xattrs](https://en.wikipedia.org/wiki/Extended_file_attributes) rather than in a single location, making manual analysis more difficult.

With this "replace File Integrity" mentality, a Bash script named `runDiffLens.sh` was written and included in this repository. Now, `difflens` is already configured in the `setup.py` to provide a console entry point. This means installation of DiffLens via Pip also adds `difflens` to the PATH by placing a wrapper in a directory such as `/usr/bin`. RunDiffLens acts as an orchestrator around difflens, providing argument population, concurrent executions for each disk in Unraid, and background processing via `screen`. Furthermore, since Unraid operates similar to a Live CD where it loads OS archives off a USB disk and then executes from memory, the OS is created from scratch at each power cycle. Python, Pip, and any customizations are wiped at each reboot and must be reinstalled by Unraid plugins, the `/boot/config/go` file, or by other means. Since `difflens` is never guaranteed to be installed right away, RunDiffLens provides offline installation of `difflens` plus its dependencies via `pip3`'s `--no-index --find-links` feature. Assuming a user has previously used `pip3 download` to save `.whl` wheel files of the necessary dependencies of DiffLens plus the `.whl` for DiffLens itself, RunDiffLens can install and execute `difflens` in a self-contained manner. Then by writing a daily, weekly, or monthly Cron job pointed at RunDiffLens, scheduled scans of the Unraid array can occur. 

## Development

There is still plenty of room to grow. Among the many directions DiffLens could travel, some TODOs and ideas are below:
- Automated integration of Pipenv's Pipfile and Pipfile.lock dependencies into `setup.py()`'s `install_requires`
- Migration of static `setup.py()` content to a `setup.cfg` as recommended by [PyPA](https://packaging.python.org/tutorials/packaging-projects/#configuring-metadata)



# TODO: unraid notification triggers, maybe from within python? Or from the CLI, passing it into the screen after difflens returns
# TODO: read an exclude file to avoid certain directories or file extensions
# TODO: split out modified files into what we have now or validating file modified date too.
# TODO: maybe also output hashing date to the output file? seconds granularity is enough
# TODO: revisit the diff validation, as if no output file was given then there's no point running at all. AKA there could be a way for absolutely nothing to be done after the scan
# TODO: revisit MIT or GPLV3 or some other license
# TODO: maybe bundle the shell script into the wheel, install it alongside, and point to that? But then we'd need a circular dependency.'
# TODO: Look at https://github.com/lovesegfault/beautysh for other tweaks and tips. CI integration with github? simple unit test to confirm arg parsing?
# TODO rename to difflens instead of difflens-kubedzero?
# TODO look at commits and then publish to github
# TODO concatenation of output files. Validate their col names match, validate unique filename, load and then output
# TODO do I also need utils to import? or are the relative imports enough, and there's no need to mention in packages?
# TODO reorganize signatures so loggers need to be passed around less
# TODO clarify duplicates. Against itself? itself + comparison? only against comparison? dictated by join type