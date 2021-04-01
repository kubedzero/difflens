# DiffLens


## Overview

DiffLens (or difflens) is a package to compute, export, and analyze BLAKE3 file hashes and directory structures. Provided with a directory input, it will scan for files under that directory and compute BLAKE3 hashes based on their contents. If reading the entire file is too slow, options are provided for reading only the first 1 megabyte of each file, or even to treat the file size as the "hash." Once the directory is scanned and these hashes are computed, the aggregated set of hashes can be written to disk.

This is where things start to get interesting. DiffLens can then read in a separate set of hashes from a previous scan and compare it to the new hashes. This enables a user of DiffLens to identify files that have changed their contents since the last scan, as well as see which files have been added or deleted when compared to the last scan. Even if a comparison set of hashes isn't passed in, DiffLens can still do some analysis on only the files it just scanned, such as looking for files with duplicate content. 


## More Information

This project's hashing is powered by [BLAKE3](https://github.com/BLAKE3-team/BLAKE3), the successor to [BLAKE2b/2s](https://www.blake2.net/). BLAKE3 promises to be "much faster than MD5, SHA-1, SHA-2, SHA-3, and BLAKE2" so the bottleneck for DiskLens is most probably a disk's I/O rather than a CPU. 

This project's analysis is powered by [pandas](https://pandas.pydata.org/), an industry-standard data manipulation and analysis library. Once the BLAKE3 hashes are computed, they're loaded into pandas DataFrames to run all the analysis mentioned above, and then output to disk in tabular format


## Unraid & `runDiffLens.sh`

Inspiration for DiffLens came from Bergware's [File Integrity](https://github.com/bergware/dynamix/tree/master/source/file-integrity) plugin for the Unraid NAS OS. It was used for weekly scans of all disks in the array to catch any [bit rot](https://en.wikipedia.org/wiki/Data_degradation) causing corrupted or inaccessible files on the array. Some functionality was lacking however, such as re-analysis of old executions, false positives due to non-Linux OSs updating files via network protocols such as Samba(SMB), and easy inspection of performance. Furthermore, File Integrity does not have BLAKE3 as a hashing option, and stores hashes in the [xattrs](https://en.wikipedia.org/wiki/Extended_file_attributes) rather than in a single location, making manual analysis more difficult.

With this "replace File Integrity" mentality, a Bash script named `runDiffLens.sh` was written and included in this repository. Now, `difflens` is already configured in the `setup.py` to provide a console entry point. This means installation of DiffLens via Pip also adds `difflens` to the PATH by placing a wrapper in a directory such as `/usr/bin`. RunDiffLens acts as an orchestrator around difflens, providing argument population, concurrent executions for each disk in Unraid, and background processing via `screen`. Furthermore, since Unraid operates similar to a Live CD where it loads OS archives off a USB disk and then executes from memory, the OS is created from scratch at each power cycle. Python, Pip, and any customizations are wiped at each reboot and must be reinstalled by Unraid plugins, the `/boot/config/go` file, or by other means. Since `difflens` is never guaranteed to be installed right away, RunDiffLens provides offline installation of `difflens` plus its dependencies via `pip3`'s `--no-index --find-links` feature. Assuming a user has previously used `pip3 download` to save `.whl` wheel files of the necessary dependencies of DiffLens plus the `.whl` for DiffLens itself, RunDiffLens can install and execute `difflens` in a self-contained manner. Then by writing a daily, weekly, or monthly Cron job pointed at RunDiffLens, scheduled scans of the Unraid array can occur. 

## Performance

An example of a DiffLens execution's logging can be found below. It can be observed that DiffLens averaged almost 160 megabytes per second of hashing speed over a 17 hour period while processing 125,000 files and 10TB. Other executions on HDDs have had up to 200MBps sustained read speeds, and executions on NVMe SSDs have had 600MBps. 

In terms of CPU usage, an Ivy Bridge EP CPU running at 2.4GHz was able to handle 550MBps of hashing from three HDDs concurrently at about 60% CPU utilization. A Skylake CPU running at 2.7GHz in a laptop was able to handle 600MBps of hashing from an NVME SSD at about 15% CPU utilization.

In terms of memory usage, DiffLens hashes files by reading 1MB at a time from disk. For this reason, any size of file can be read, practically regardless of system memory available. However, memory is a constraint when storing and processing the hashes. As files are processed, their attributes and hashes are stored in Dictionary and List objects as Strings, so an eventual memory limit will be reached. From experience, 300,000 files hashed resulted in around 300MB of memory usage. This is not a strictly linear scale, as hashing fewer than 100 files still resulted in a "base" memory usage of around 50MB. 

```
2021-03-29T21:30:54-0700[WARNING][Executor]: Starting diff-lens from current working directory /mnt/disk3
2021-03-29T21:30:54-0700[INFO][Executor]: Beginning directory scan and file hash computation of files in .
2021-03-30T14:50:14-0700[INFO][IO]: 9925463.8MB of data read from disk across 5894 directories & 123932 files in 1039.34 minutes at 159MBps, or 119 files per minute
2021-03-30T14:50:14-0700[INFO][Executor]: Directory scan and file hash computation complete. Flattening output into DataFrame
2021-03-30T14:50:14-0700[INFO][Executor]: RAM used by Python process: 195.4MB
2021-03-30T14:50:14-0700[INFO][IO]: Writing newly computed full file hashes for 123932 files to disk at /boot/logs/2021-03-29PT2130-disk3-hashes.tsv.gz
2021-03-30T14:50:17-0700[INFO][Executor]: Beginning analysis of Current DataFrame with 123932 rows
2021-03-30T14:50:17-0700[INFO][Executor]: Finding duplicates in Current DataFrame based on hash
2021-03-30T14:50:17-0700[INFO][IO]: Writing Duplicate DataFrame with 12958 rows across 4838 groups to disk at /boot/logs/2021-03-29PT2130-disk3-duplicates.tsv.gz
2021-03-30T14:50:18-0700[INFO][IO]: Reading Comparison DataFrame from disk at /boot/logs/2021-03-28PT2213-disk3-hashes.tsv.gz
2021-03-30T14:50:19-0700[INFO][Executor]: Finding files in the comparison_data_frame that have been (Re)moved
2021-03-30T14:50:20-0700[INFO][IO]: Writing (Re)moved DataFrame with 0 rows to disk at /boot/logs/2021-03-29PT2130-disk3-removed.tsv.gz
2021-03-30T14:50:20-0700[INFO][Executor]: Finding files in the comparison_data_frame that have been Added
2021-03-30T14:50:21-0700[INFO][IO]: Writing Added DataFrame with 0 rows to disk at /boot/logs/2021-03-29PT2130-disk3-added.tsv.gz
2021-03-30T14:50:21-0700[INFO][Executor]: Finding files with different hashes than their Comparison DataFrame counterparts
2021-03-30T14:50:21-0700[INFO][IO]: Writing Modified DataFrame with 0 rows to disk at /boot/logs/2021-03-29PT2130-disk3-modified.tsv.gz
2021-03-30T14:50:22-0700[WARNING][Executor]: Shutting down diff-lens
```


## Development


### TODO

There is still plenty of room to grow. Among the many directions DiffLens could travel, some TODOs and ideas are below:
- Automated integration of Pipenv's Pipfile and Pipfile.lock dependencies into `setup.py()`'s `install_requires`
- Migration of static `setup.py()` content to a `setup.cfg` as recommended by [PyPA](https://packaging.python.org/tutorials/packaging-projects/#configuring-metadata)
- Revisiting whether the MIT license is appropriate, as the desire is for notification to be provided if this project were used as part of another, or part of a paid product
- Adding Unraid UI/email notifications when a DiffLens execution completes
- Parsing of an Exclude file, similar to `.gitignore` format, used to skip over certain directories or file extensions
- Splitting the modified file output into separate jobs for purely modified files, or files that also received updated modification dates
- More analysis of file size, since any file processed should also have file size. This could be used to determine space lost due to duplicates, the size by which files grew/shrunk, sorting by file size, and more
- Outputting the hashing date to the file with a granularity in seconds
- Optimizing the conditional behavior, as it's possible right now to do a scan but not act on it when no output or analysis flags are given
- Possibly bundle the script or other support files into the build so they're installed to Unraid alongside the Python files. This would prevent users from separately downloading the Bash script, but runs into the chicken-and-egg problem of the script containing installation commands for what ends up being itself
- Unit tests that validate argument parsing works as expected, or that helper functions perform in the desired manner
- Continuous Integration and/or delivery via GitHub Actions to run unit tests and/or build wheel outputs upon commit
- Determine if the setup should name the package `difflens` or `difflens-kubedzero` as the name influences how it shows up in Pip
- Add another utility or flag to concatenate multiple hash files. This can be used to ensure uniqueness of files across all Unraid disks, as well as to find duplicates that may have been spread out across other disks. Finally, it could be used to eliminate false positives of deleted/added files if said files were moved from one disk to another while keeping the same relative path
- Reorganize the helpers into Classes so they can be initialized with loggers, which would eliminate the need for loggers to be passed via argument
- Add duplicate analysis between two files. This could work by joining on hash and then removing rows where the original and comparison have the same path, which would leave only files having the same hash but different relative paths. In lieu of a concatenation utility, this could assist with finding duplicates across disks. For a three-disk setup, checking 1-2, 2-3, and 1-3 would ensure all possible duplicates are found. 


## Resources and References

- https://github.com/lovesegfault/beautysh provided some guidance on building a Python project that is also available outside Python via the shell
- 