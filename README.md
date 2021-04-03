# DiffLens


## Overview

DiffLens (or difflens) is a package to compute, export, and analyze BLAKE3 file hashes and directory structures. Provided with a directory input, it will scan for files under that directory and compute BLAKE3 hashes based on their contents. If reading the entire file is too slow, options are provided for reading only the first 1 megabyte of each file, or even to treat the file size as the "hash." Once the directory is scanned and these hashes are computed, the aggregated set of hashes can be written to disk.

This is where things start to get interesting. DiffLens can then read in a separate set of hashes from a previous scan and compare it to the new hashes. This enables a user of DiffLens to identify files that have changed their contents since the last scan, as well as see which files have been added or deleted when compared to the last scan. Even if a comparison set of hashes isn't passed in, DiffLens can still do some analysis on only the files it just scanned, such as looking for files with duplicate content. 


## More Information

This project's hashing is powered by [BLAKE3](https://github.com/BLAKE3-team/BLAKE3), the successor to [BLAKE2b/2s](https://www.blake2.net/). BLAKE3 promises to be "much faster than MD5, SHA-1, SHA-2, SHA-3, and BLAKE2" so the bottleneck for DiskLens is most probably a disk's I/O rather than a CPU. 

This project's analysis is powered by [pandas](https://pandas.pydata.org/), an industry-standard data manipulation and analysis library. Once the BLAKE3 hashes are computed, they're loaded into pandas DataFrames to run all the analysis mentioned above, and then output to disk in tabular format


## Unraid & `runDiffLens.sh`

Inspiration for DiffLens came from Bergware's [File Integrity](https://github.com/bergware/dynamix/tree/master/source/file-integrity) plugin for the Unraid NAS OS. It was used for weekly scans of all disks in the array to catch any [bit rot](https://en.wikipedia.org/wiki/Data_degradation) causing corrupted or inaccessible files on the array. Some functionality was lacking however, such as re-analysis of old executions, false positives due to non-Linux OSs updating files via network protocols such as Samba(SMB), and easy inspection of performance. Furthermore, File Integrity does not have BLAKE3 as a hashing option, and stores hashes in the [xattrs](https://en.wikipedia.org/wiki/Extended_file_attributes) rather than in a single location, making manual analysis more difficult.

With this "replace File Integrity" mentality, a Bash script named `runDiffLens.sh` was written and included in this repository. Now, `difflens` is already configured in the `setup.py` to provide a console entry point. This means installation of DiffLens via Pip also adds `difflens` to the PATH by placing a wrapper in a directory such as `/usr/bin`. RunDiffLens acts as an orchestrator around `difflens`, providing argument population, concurrent executions for each disk in Unraid, and background processing via `screen`. Furthermore, since Unraid operates similar to a Live CD where it loads OS archives off a USB disk and then executes from memory, the OS is created from scratch at each power cycle. Python, Pip, and any customizations are wiped at each reboot and must be reinstalled by Unraid plugins, the `/boot/config/go` file, or by other means. Since `difflens` is never guaranteed to be installed right away, RunDiffLens provides offline installation of `difflens` plus its dependencies via `pip3`'s `--no-index --find-links` feature. Assuming a user has previously used `pip3 download` to save `.whl` wheel files of the necessary dependencies of DiffLens plus the `.whl` for DiffLens itself, RunDiffLens can install and execute `difflens` in a self-contained manner. Then by writing a daily, weekly, or monthly Cron job pointed at RunDiffLens, scheduled scans of the Unraid array can occur. 

[Dynamix](https://github.com/bergware/dynamix) started off as a Bergware-developed GUI for Unraid, but eventually became part of the core distribution. Unraid now has built-in functionality to look for and install any file ending in `.cron` that exists in the directory `/boot/config/plugins/dynamix/`. Thus, a new file can be created `nano /boot/config/plugins/dynamix/runDiffLens.cron` with a Cron-format line inside, such as  `0 23 * * 0  /boot/runDiffLens.sh > /boot/logs/latest_difflens_run.log 2>&1` . This example would run at time 23:00 on each week/month on day 0 of the week, Sunday. At that time it will execute `/boot/runDiffLens.sh` and output the STDERR *and* STDOUT (thanks to `2>&1` and `>`) to a file `/boot/latest_difflens_run.log`. Note that this new Cron entry won't automatically be installed. Either `/usr/local/sbin/update_cron` will have to be run, which rescans the directory for `.cron` files, or Unraid can be rebooted. The Cron daemon reads from `/etc/cron.d/root`, so inspect that to see the registered/active Cron commands. 

A common pattern within Unraid is to cache plugin and package files on the USB drive and then install from there, rather than fetching new  files from the Internet on each boot. This practice can be followed for DiffLens and Pip as well. By using `pip3 download package1 package2`, the files `package1.whl` and `package2.whl` will be downloaded and stored on disk. This can be used to download and store the dependencies of DiffLens in a folder on the USB `/boot/` disk. From there, when installing DiffLens, `pip3 install /boot/python_wheels/difflens* --no-index --find-links file:///boot/python_wheels` can install DiffLens and all its dependencies in an entirely offline manner. 

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

### IDE, Environment, and Building

macOS Big Sur 11.2.3 was the host operating system used to develop DiffLens

- `xcode-select --install` was used to ensure the Xcode command line tools were installed and up to date. This gets `python3` and `pip3`  installed in the macOS system-owned `/usr/bin` alongside other dependencies used later.
- At this stage, the PATH should have no other copies of Python or Pip. 
  - This can be validated with `which -a python pip python3 pip3` 
  - The PATH itself can be inspected with `echo $PATH` and at this stage should look something similar to `/usr/local/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`. 
  - This is mentioned because there had previously been manually-installed Python, macOS installed Python, and easy_install installed Python, all of which were cluttering the PATH. 
- [Homebrew](https://docs.brew.sh/Installation) was used as the base package manager. 
  - `brew install python@3.9` was coincidentally installed to `/usr/local/bin/python3` for other Homebrew formulae, but the goal should be to avoid using this, as a more favored approach will be introduced next.
- [Pyenv](https://github.com/pyenv/pyenv) is the recommended method of managing multiple Python installs, and can be installed with `brew install pyenv`.  
  - Once installed, `pyenv install --list` can display all the installable versions of Python. 
  - Proceed with `pyenv install 3.9.2` which was the latest as of writing. 
  - Then `pyenv rehash` and `pyenv global 3.9.2` to rehash the shim and set 3.9.2 to the global default. 
  - Finally, following https://github.com/pyenv/pyenv#installation, `pyenv init` needs to be added to the PATH printout by adjusting the ZSH config with `echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.zshrc`. 
  - Then a reload of the shell with `exec "$SHELL"` will apply the changes. 
  - After this step, running `echo $PATH` should show pyenv present at the front of the PATH: `/Users/kz/.pyenv/shims:/usr/local/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin` This allows any calls to `python3` or `pip3` or `pipenv` to  be intercepted by Pyenv before the brew- or system-installed versions can be used. 
  - `which -a python pip python3 pip3` can again be run at this step, but this time should print out lines such as `/Users/kz/.pyenv/shims/python3` that indicate Pyenv's shim is working as expected.
  - Now, any calls to `pip3` or `python3` in the shell will use the Pyenv shim versions at `/Users/kz/.pyenv/shims/python3` and `/Users/kz/.pyenv/shims/pip3`
- [Pipenv](https://github.com/pypa/pipenv) is next on the install list, but will be installed with Pip instead of Homebrew: `pip3 install pipenv`
  - Running `which -a pipenv` should show a copy under Pyenv `/Users/kz/.pyenv/shims/pipenv` but no others, as the Pyenv-owned `pip3` should have installed it. 
  - https://realpython.com/pipenv-guide/ goes into detail on why this is needed, but the gist of it is that it allows isolated sets of Pip packages to be related to a single project, rather than all projects sharing the system's single Pip install and interfering with one another's dependencies. 
  - This will be discussed more later on, but Pipenv enables the replacement of a project's `requirements.txt` with the more-powerful `Pipfile` and `Pipfile.lock`
  - https://pipenv-fork.readthedocs.io/en/latest/basics.html has a good description of the common commands
- It seems that Pipenv under the hood uses a Python module called `maturin` which may in turn use `cargo`, the package manager for the [Rust](https://www.rust-lang.org) language. 
  - When Rust was not installed, an error was experienced when trying to run `pipenv install <package>`. Specifically, the `pipenv` STDOUT stalls on `Locking...` and then outputs a stack trace with `Could not build wheels for maturin which use PEP 517 and cannot be installed directly` and `cargo not found in PATH. Please install rust (https://www.rust-lang.org/tools/install) and try again`
  - For this reason, Rust can be installed via Homebrew with `brew install rustup`, which installs utilities `rustc`, `cargo`, and `rustup-init`. 
  - https://sourabhbajaj.com/mac-setup/Rust/ provided instructions for the process
  - Run `rustup-init` to add `rustc` and `cargo` to the PATH by editing `.zshenv` and `.profile` or another shell's config. `source "$HOME/.cargo/env"` appears to have been added to both. 
  - Run `exec "$SHELL"` to reload the shell with the new PATH (or open a new terminal window)
  - Then `which -a cargo` results in `/Users/kz/.cargo/bin/cargo`
- General Pipenv CLI usage
  - Pipenv's purpose is to allow each directory/project containing Python code to have a disjoint set of installed Pip dependencies. Furthermore, it creates `Pipfile` and `Pipfile.lock` files in the directory/project to describe the state of Pip for that project. 
  - This allows for conflicting versions across different projects to be installed simultaneously, and also allows for concrete dependency resolution to ensure that a new instance of the project can reinstall the exact same dependency state as the original. 
  - https://realpython.com/pipenv-guide/ goes into more detail about the purpose of Pipenv, as does https://pipenv-fork.readthedocs.io/en/latest/basics.html 
  - `pipenv shell` when executed in a project directory will look for a virtual environment already associated with the directory. 
    - If a virtual env does not exist, it will create a new one, possibly in `/Users/kz/.local/share/virtualenvs/`. It will then drop the caller into the pipenv shell. NOTE: PyCharm's UI can also create a virtual environment, so that was used for initialization rather than running `pipenv shell` first
    - This shell updates the PATH to start with the virtual environment copies of `python3` and `pip`, isolating any changes to this particular project. Note that `which -a pipenv` will still show the original install location of `/Users/kz/.pyenv/shims/pipenv` so being in the shell versus not doesn't matter to `pipenv`. 
    - `exit` will exit out of the Pipenv shell and return the caller to the normal shell with the system-shared `pip3` and `python3`
  - `pipenv --rm` will delete the virtual environment, which could be good for starting from scratch
  - To add a package to a project such that it is declared in the `Pipfile`, run `pipenv install <somePackage>` either from inside or outside the Pipenv shell. It will install it into the virtual env's `pip3` and then add the package into the Pipfile. NOTE: This command is known to hang for a long time and consume many system resources, including high CPU and lots of network/download.
  - To undo a package installation, `pipenv uninstall <somePackage` will remove it from the `Pipfile` and uninstall it from `pip3`. If `pip3 uninstall somePackage` was run, the `Pipfile` would remain unchanged and Pipenv would still reinstall it. 
  - To generate/update the `Pipfile.lock` that tracks the exact dependency versions of the declared packages and all their transitive dependencies, run `pipenv lock` 
  - In a freshly created virtual environment, `pipenv sync` can be run to load all the dependencies from the `Pipfile.lock` into `pip3`. `pipenv install` will also work, but may install package versions not defined in the lock file. In other words, `pipenv sync` will perfectly recreate the environment, while `pipenv install` could install different package versions. In the old style before Pipenv with a single `requirements.txt`, the closest a user could get to replicating a build environment was re-downloading the top-level package versions defined, rather than the entire dependency graph.
- [JetBrains PyCharm](https://www.jetbrains.com/pycharm/) 2020.3 was the IDE used to develop DiffLens
  - The Python Interpreter is the first thing to set up. PyCharm may offer to "create a pipenv from a Pipfile" banner when it discovers that no interpreter is set up for the project. If selected, it should grab the already-created Pipfile and configure the whole Pipenv with no further action.
  - To set up a Python Interpreter manually, open the Preferences and then go to Project > Python Interpreter > Gear > Show All and then click the plus button. Instead of a Virtualenv Environment, choose PipEnv Environment from the left side. Ensure the Base Interpreter is pulling from Pyenv's copy of Python3, namely `/Users/kz/.pyenv/shims/python3`, and that the Pipenv Executable is similarly pulling `/Users/kz/.pyenv/shims/pipenv`. It's fine to also check the "Install packages from Pipfile" as that saves a step of manually syncing the Pipenv. 
  - There should be no need to mark the `./difflens` or `./difflens/util` directories as source files, because they should be picked up by default as Namespace Packages due to the presence of `__init__.py` files in each. It won't hurt to do so, though
  - The Terminal tab in PyCharm may automatically drop into the `pipenv shell` mode, which can be seen when running `which -a pip3` and getting a virtual environment first on the list, rather than the system-wide `/Users/kz/.pyenv/shims/pip3`. If it doesn't, `pipenv shell` can be run and a message similar to `Pipenv found itself running within a virtual environment, so it will automatically use that environment, instead of creating its own for any project` may be seen
  - DiffLens can be executed in a variety of ways from PyCharm:
    - One option is to make a Run Configuration. A shortcut is to find the green Play button in the gutter next to the line containing `if __name__ == "__main__":`, with the option to either run it directly or to edit the Run Configuration. If run directly without any modification, DiffLens should execute but note that input arguments weren't given. For this reason, going to edit the Run Configuration (either by that Play button or by the dropdown at the top right of PyCharm) is necessary. Once there, some important settings can be seen. For one, Script Path can be changed to Module name if it's desired to run DiffLens in Module mode (`python3 -m difflens.entry`), though aside from import behavior there should be little difference. The Parameters box (expandable on the right side) is the important bit, as that's where `--scan-directory ~/Downloads` or whatever else can be entered in. The Working directory is also vital, as that would simulate calling DiffLens from outside the project files. Since Difflens stores relative paths based on the working directory, this can be modified from the project directory to some other place (such as `~/Downloads`) to simulate running `difflens` from that directory.
    - Another option is to use the Terminal tab at the bottom. After confirming with `which -a pip3 && pip3 list` that the Pipenv packages are installed and being used, run DiffLens in module mode with `python3 -m difflens` or `python3 -m difflens.entry` and then any of the input arguments desired. 
    - Also possible from the Terminal is running DiffLens in file mode, such as with `python3 difflens/entry.py`. However, the current state if the project is probable to yield an ImportError, even though running the same file mode command in PyCharm does not error out. This could be due to PyCharm's Run Configurations setting the [PYTHONPATH](https://bic-berkeley.github.io/psych-214-fall-2016/using_pythonpath.html) environment variable to include the project's source code and Namespace directories, whereas running from the Terminal won't have this automatically set 
- [Building]( https://packaging.python.org/tutorials/packaging-projects/)
  - Building DiffLens serves the purpose of taking all the source code and metadata and collecting it into a single `.whl` file or other install-ready format for distribution to other systems. From there, another system with `pip3` installed can simply run `pip3 install path/to/difflens.whl` to install not just DiffLens, but all its dependencies. 
  - `pip3 install build` is used to install the build tools necessary to run build commands. Note that `pip3 install` is used here instead of `pipenv install` which serves the purpose of installing the `build` package and its dependencies in the virtual env without adding them to the `Pipfile`
  - Then, `python3 -m build --wheel` can be run to collect the source code and actually create a folder `dist/`, and under it the wheel file: `difflens_kubedzero-0.1-py3-none-any.whl`
  - This `build --wheel` command takes the information contained in `setup.py` and `setup.cfg` to determine **how** to build the wheel. For example:
    - `packages=setuptools.find_packages()` is a shortcut for `packages=["difflens"]` where Setuptools automatically runs through the repository's directory to find Python packages as indicated by a presence of `__init__.py`
    - `entry_points={"console_scripts": ["difflens = difflens.entry:main"]}` tells the wheel file to contain special instructions to create a CLI wrapper in the PATH called `difflens` that automatically runs the `main` function inside the module `difflens.entry`
    - `install_requires=["blake3~=0.1.8", "pandas~=1.2.3", "psutil~=5.8.0"]` tells Pip that, when installing, these other dependencies should also be installed if they aren't already. The `~=` indicates that compatible versions are OK and that they don't need to be exactly the same version.


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

- https://github.com/lovesegfault/beautysh provided some guidance on building a simple Python project that is also accessible via the shell
- https://stackoverflow.com/questions/48628417/how-to-select-rows-in-pandas-dataframe-where-value-appears-more-than-once helped determine how to use Pandas to find rows where a hash value was seen more than N times, where in this case N>=2
- https://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python helped when the original code ran into MemoryError during execution. This was probably due to trying to read a file bigger than the available memory, an issue common with all hashers. The solution was to read the file one chunk at a time, provided that the hasher had an `update()` method (which BLAKE3 did thankfully)
- https://github.com/oconnor663/blake3-py/blob/master/src/lib.rs#L141 had something to say about the multithreading feature of BLAKE3: "updating one hasher from multiple threads is a very odd thing to do, and real world program almost never need to worry about it." This kind of makes sense, as one can't really read from a spinning disk in a multithreaded manner. The only instance where multithreading might be handy is if a CPU core is maxed out trying to hash, aka hitting the GHz/IPC limit of the CPU
- https://packaging.python.org/overview/#python-binary-distributions and https://packaging.python.org/tutorials/packaging-projects/ had great information on packaging/building Python projects, and pointed to https://pypi.org/project/pipenv/ after saying "Virtualenvs have been an indispensable tool for multiple generations of Python developer, but are slowly fading from view, as they are being wrapped by higher-level tools"
- https://nuitka.net/pages/overview.html and Cython seemed to be alternate versions of packaging where Python might not actually need to be installed. That said, it was not exactly what was needed here and thus not investigated further. 
- https://packaging.python.org/tutorials/packaging-projects/#configuring-metadata and https://packaging.python.org/guides/distributing-packages-using-setuptools/ and https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html all contain supporting information on other parameters that can go into `setup.py` and `setup.cfg`
- https://docs.python.org/3/tutorial/modules.html#packages had some good information on how imports work at different levels
- Python naming conventions
  - https://www.python.org/dev/peps/pep-0008/#package-and-module-names
  - https://softwareengineering.stackexchange.com/questions/308972/python-file-naming-convention
- https://stackoverflow.com/questions/3229419/how-to-pretty-print-nested-dictionaries had a useful helper function to print out a dict in a more easy to read format
- Pandas
  - https://stackoverflow.com/questions/13784192/creating-an-empty-pandas-dataframe-then-filling-it interestingly, this notes that creating a dataframe and then filling it in a loop is a bad thing to do, and it's much more memory efficient to create a list and then create the DataFrame from that list. 
  - https://docs.python.org/3/library/csv.html#csv.DictReader has information on how to read a CSV file from disk and ingest it as a DataFrame
  - https://docs.python.org/3/library/pickle.html Pickling was another on-disk data format, but was not human readable. 
- https://github.com/giampaolo/psutil was a package used to fetch RAM/CPU usage of a currently-running Python application
- https://github.com/pypa/pipenv/issues/598 provides guidance that both Pipfile and Pipfile.lock should be tracked and committed in Git
- `python -c "help('modules')"` can be used to print out all modules currently available within python. This should print out modules installed by pip as well, so this can help verify that a wheel installation actually happened
  - https://www.activestate.com/resources/quick-reads/how-to-list-installed-python-packages/
  - https://stackoverflow.com/questions/16908236/how-to-execute-python-inline-from-a-bash-shell/16908265
- https://www.activestate.com/resources/quick-reads/how-to-update-all-python-packages/ provides instructions for how to check which Pip packages are outdated, and how to update them in bulk
  - `pip list --outdated` to check
  - `pip3 list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip3 install -U ` to update
  - `pipenv update` can also be used to update declared dependencies, followed by a `pipenv lock` to update `Pipfile.lock`
- https://pep8.org/#imports provides guidance on how to properly structure imports
- https://realpython.com/python-modules-packages/ and https://realpython.com/absolute-vs-relative-python-imports/ provide verbose descriptions of modules, packages, and imports
- https://realpython.com/python-wheels/#telling-pip-what-to-download goes into the benefits of wheels:
  - Wheels install faster than source distributions for both pure-Python packages and extension modules.
  - Wheels are smaller than source distributions. For example, the `six` wheel is about one-third the size of the corresponding source distribution. This differential becomes even more important when considering that a pip install for a single package may actually kick off downloading a chain of dependencies.
  - Wheels cut setup.py execution out of the equation. Installing from a source distribution runs whatever is contained in that project’s setup.py. As pointed out by PEP 427, this amounts to arbitrary code execution. Wheels avoid this altogether.
  - There’s no need for a compiler to install wheels that contain compiled extension modules. The extension module comes included with the wheel targeting a specific platform and Python version.
  - pip automatically generates .pyc files in the wheel that match the right Python interpreter.
  - Wheels provide consistency by cutting many of the variables involved in installing a package out of the equation.
- Getting Python set up correctly on macOS
  - https://opensource.com/article/19/5/python-3-default-mac helped a ton in 
  - Homebrew recommended running ``sudo rm -rf /Library/Developer/CommandLineTools` and then allowing it to reinstall just to make sure it was up to date
  - https://stackoverflow.com/questions/22051158/how-to-fully-uninstall-pip-installed-with-easy-install/22053391 helped with uninstalling the Pip that got installed via the macOS `easy_install` utility
  - https://github.com/pyenv/pyenv#installation helped with installing Pyenv, namely that running `echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.zshrc` was necessary to update the shell to reference Pyenv's shim folder
- https://stackoverflow.com/questions/3765234/listing-and-deleting-git-commits-that-are-under-no-branch-dangling getting rid of commits that are not in any branch
  - Useful when searching `git grep someSearch $(git rev-list --all) ` to try and find string occurrences that now only exist in no-longer-referenced commit IDs. NOTE that the command can be updated to `git grep someSearch $(git rev-list HEAD)` to only search in commits in the HEAD branch. 
  - `git stash clear && git reflog expire --expire-unreachable=now --all && git fsck --unreachable && git gc --prune=now` can clean things up