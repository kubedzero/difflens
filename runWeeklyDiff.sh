#!/bin/bash
# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euo pipefail

# Script to assist with running multiple diff-lens executions in parallel

# Set the max disk number to check. We expect disks will be numbered 1,2,etc. up to max_disk_num
max_disk_num=3

# Set the directory where we'll store the output files. No trailing slash
output_dir="/boot/logs"
# Set the suffix of our output files
file_suffix=".tsv.gz"

# Set the directory where we'll output logs. No trailing slash
# NOTE: not setting to /boot to avoid unnecessary writes
log_output_dir="/tmp"

# Set the directory where our .py and requirements.txt files live. No trailing slash
project_dir="/boot/python/diff_lens"
# Set the directory where we store dependency Wheel files
dependency_wheel_dir="/boot/python/package_wheels"

# Get the date, which we'll use to name our output files
run_date=$(date '+%Y-%m-%dPT%H%M')

# Check that dependencies are installed by defining their full paths and checking that they exist
# This bypasses any sort of PATH snafu when running from Cron
# https://linuxize.com/post/bash-check-if-file-exists/
screen_path="/usr/bin/screen"
python3_path="/usr/bin/python3"
pip3_path="/usr/bin/pip3"
if [[ -z "$screen_path" || -z "$python3_path" || -z "$pip3_path" ]]; then
  echo "One or more of $screen_path $python3_path $pip3_path did not exist and is required for operation. Exiting"
  exit 1
fi

# Use pip3 to handle dependency install
# -r points to a requirements.txt
# --no-index will ignore the package index, must also pass in --find-links
# https://www.codegrepper.com/code-examples/shell/pip+install+from+requirements.txt
# https://stackoverflow.com/questions/7225900/how-can-i-install-packages-using-pip-according-to-the-requirements-txt-file-from
echo "Installing project dependencies using pip3"
$pip3_path install -r $project_dir/requirements.txt --no-index --find-links file://$dependency_wheel_dir

echo "Assembling input arguments and starting screens for each disk"
# https://stackoverflow.com/questions/169511
for disk_num in $(seq 1 $max_disk_num); do
  # Construct the root of our output files. All outputs will share this prefix and path
  output_file_root="$output_dir/$run_date-disk$disk_num"
  # Construct the path where we'll store the full scan's hash list
  output_hash_file="$output_file_root-hashes$file_suffix"
  # Construct the path where we'll store the removed files list
  output_removed_files="$output_file_root-removed$file_suffix"
  # Construct the path where we'll store the added files list
  output_added_files="$output_file_root-added$file_suffix"
  # Construct the path where we'll store the modified files list
  output_modified_files="$output_file_root-modified$file_suffix"
  # Construct the path where we'll store the duplicate files list
  output_duplicates="$output_file_root-duplicates$file_suffix"

  # Find the previous hash to diff against.
  # Since we prefix the filenames with date, we can sort and get the last line to find the most recent file
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
  echo "Previous hash file we'll compare disk$disk_num against is $previous_hash_file"

  # Construct the path to the disk, which we use as the working directory
  cd "/mnt/disk$disk_num"

  # Construct the list of input arguments
  # https://stackoverflow.com/questions/46807924/bash-split-long-string-argument-to-multiple-lines
  diff_lens_args="--scan_directory . \
  --output_hash_file $output_hash_file \
  --comparison_hash_file $previous_hash_file \
  --output_removed_files $output_removed_files \
  --output_added_files $output_added_files \
  --output_modified_files $output_modified_files \
  --output_duplicates $output_duplicates  \
  --log_update_interval_seconds 60"

  # Construct the full command used to start up diff-lens. We'll trigger this with bash
  diff_lens_command="$python3_path $project_dir/run.py $diff_lens_args"
  # Construct the screen session name
  screen_name="diff-lens-disk$disk_num"

  # Run the script in a detached screen session
  # -L required to enable logs. -Logfile to specify where. -S to name the session. -dm <cmd> to run <cmd> in screen
  # https://superuser.com/questions/454907/how-to-execute-a-command-in-screen-and-detach
  # https://fvdm.com/code/howto-write-screen-output-to-a-log-file
  $screen_path -L -Logfile "$log_output_dir/$run_date-$screen_name.log" -S "$screen_name" -dm bash -c "$diff_lens_command"
  echo -e "Monitor logs at $log_output_dir/$run_date-$screen_name.log for Screen with name $screen_name\n\n"
done

echo "Screens started for $max_disk_num diff-lens executions. Use screen -r <name> to connect."
# https://github.com/koalaman/shellcheck/wiki/SC2005
$screen_path -list
