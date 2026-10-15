#!/bin/bash
# Copy one source directory into each target listed in a file.
# Layout: target_dir/name_of_source_dir/...

set -euo pipefail

if [[ $# -ne 2 ]]; then
	echo "Usage: $(basename "$0") SOURCE_DIR TARGETS_FILE" >&2
	exit 1
fi

source_dir=${1%/}
targets_file=$2

if [[ -z $source_dir || ! -d $source_dir ]]; then
	echo "Source is not a directory: $1" >&2
	exit 1
fi
if [[ ! -f $targets_file || ! -r $targets_file ]]; then
	echo "Targets file is not readable: $targets_file" >&2
	exit 1
fi

while IFS= read -r target || [[ -n ${target:-} ]]; do
	target=${target%$'\r'}
	target=${target%/}
	[[ -z $target ]] && continue
	if [[ ! -d $target ]]; then
		echo "Target is not a directory: $target" >&2
		exit 1
	fi
	rsync -av -- "$source_dir" "$target/"
done < "$targets_file"
