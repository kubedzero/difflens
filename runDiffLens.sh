#!/bin/bash
# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euo pipefail

# Script to assist with running multiple difflens executions in parallel

# Set the max disk number to check. Disks should be numbered 1,2,...,max_disk_num
max_disk_num=3

# Set the directory where difflens will write its output files. No trailing slash
output_dir="/boot/logs"
# Set the suffix of the output files
file_suffix=".tsv.gz"

# Set the directory where screen will output logs. No trailing slash
# NOTE: not setting to /boot to avoid unnecessary writes
log_output_dir="/tmp"

# Set the directory where dependency Wheel files are stored
dependency_wheel_dir="/boot/python_wheels"

# Get the date, which is used to name the output and log files
run_date=$(date '+%Y-%m-%dPT%H%M')

# Check that dependencies are installed by defining their full paths and checking that they exist
# This bypasses any sort of PATH snafu when running from Cron
# https://linuxize.com/post/bash-check-if-file-exists/
screen_path="/usr/bin/screen"
python3_path="/usr/bin/python3"
pip3_path="/usr/bin/pip3"
notify_path="/usr/local/emhttp/webGui/scripts/notify"
hostname_path="/bin/hostname"
if [[ -z "$screen_path" || -z "$python3_path" || -z "$pip3_path" || -z "$notify_path" || -z "$hostname_path" ]]; then
    echo "One or more of $screen_path $python3_path $pip3_path $notify_path $hostname_path did not exist and is required for operation. Exiting"
    exit 1
fi

# Use pip3 to install from a wheel file created from the project's Python source
# --no-index will ignore the package index, must also pass in --find-links
# https://www.codegrepper.com/code-examples/shell/pip+install+from+requirements.txt
# https://stackoverflow.com/questions/7225900/how-can-i-install-packages-using-pip-according-to-the-requirements-txt-file-from
echo "Installing project and dependencies using pip3"
$pip3_path install $dependency_wheel_dir/difflens* --no-index --find-links file://$dependency_wheel_dir

# Set the executable that pip3 creates when installing
difflens_wrapper="/usr/bin/difflens"

echo "Assembling input arguments and starting screens for each disk"
# https://stackoverflow.com/questions/169511
for disk_num in $(seq 1 $max_disk_num); do
    # Construct the root of the output files' names. All outputs will share this prefix and path
    output_file_root="$output_dir/$run_date-disk$disk_num"
    # Construct the path where the full scan's hash list is stored
    output_hash_file="$output_file_root-hashes$file_suffix"
    # Construct the path where the removed files list is stored
    output_removed_files="$output_file_root-removed$file_suffix"
    # Construct the path where the added files list is stored
    output_added_files="$output_file_root-added$file_suffix"
    # Construct the path where the modified files list is stored
    output_modified_files="$output_file_root-modified$file_suffix"
    # Construct the path where the duplicate files list is stored
    output_duplicates="$output_file_root-duplicates$file_suffix"

    # Find the previous hash to diff against.
    # Filenames are prefixed with date, so can sort and get the last line to find the most recent file
    # https://www.geeksforgeeks.org/mindepth-maxdepth-linux-find-command-limiting-search-specific-directory/
    # https://superuser.com/questions/294161/unix-linux-find-and-sort-by-date-modified
    # https://www.cyberciti.biz/faq/search-for-files-in-bash/
    # https://www.unix.com/shell-programming-and-scripting/119458-find-most-recent-file-containing-certain-string.html
    # https://stackoverflow.com/questions/1015678/get-most-recent-file-in-a-directory-on-linux
    previous_hash_file_pattern="*-disk$disk_num-hashes$file_suffix"
    previous_hash_file=$(find "$output_dir" -type f -maxdepth 1 -name "$previous_hash_file_pattern" | sort -n | tail -1)
    # If the previous file did not exist, make a stand-in path instead of an empty string
    # https://www.cyberciti.biz/faq/unix-linux-bash-script-check-if-variable-is-empty/
    [[ -z "$previous_hash_file" ]] && previous_hash_file="no_such_file"
    echo "The files on disk$disk_num will be compared against $previous_hash_file"

    # Construct the path to the disk, which is used as the working directory.
    # This sets up the relative path stored in the output files
    cd "/mnt/disk$disk_num"

    # Construct the list of input arguments
    # https://stackoverflow.com/questions/46807924/bash-split-long-string-argument-to-multiple-lines
    difflens_args="--scan-directory . \
      --output-hash-file $output_hash_file \
      --comparison-hash-file $previous_hash_file \
      --output-removed-files $output_removed_files \
      --output-added-files $output_added_files \
      --output-modified-files $output_modified_files \
      --output-duplicates $output_duplicates  \
      --log-update-interval-seconds 60"

    # Construct the full command used to start up difflens.
    difflens_command="$difflens_wrapper $difflens_args"

    # Construct the screen session name and log path
    screen_name="disk$disk_num-difflens"
    screen_log_path="$log_output_dir/$run_date-$screen_name.log"

    # Construct Unraid notification args to indicate hostname, disk number, and log path
    # https://forums.unraid.net/topic/61996-cron-jobs-notify/
    notify_args="-s 'Difflens Finished on $($hostname_path)-disk$disk_num' -d 'Logs located at $screen_log_path'"
    notify_command="$notify_path $notify_args"

    # Add command on the difflens initiation to send an Unraid notification when finished, regardless of exit code
    daemon_command="$difflens_command; $notify_command"

    # Run the script in a detached screen session
    # -L required to enable logs. -Logfile to specify where. -S to name the session. -dm <cmd> to run <cmd> in screen
    # https://superuser.com/questions/454907/how-to-execute-a-command-in-screen-and-detach
    # https://fvdm.com/code/howto-write-screen-output-to-a-log-file
    $screen_path -L -Logfile "$screen_log_path" -S "$screen_name" -dm bash -c "daemon_command"
    echo -e "Monitor logs at $screen_log_path for Screen with name $screen_name\n\n"
done

echo "Screens started for $max_disk_num difflens executions. Use screen -r <name> to connect."
# https://github.com/koalaman/shellcheck/wiki/SC2005
$screen_path -list
