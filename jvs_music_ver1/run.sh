#!/bin/bash

set -e
set -o pipefail

function xrun () {
    set -x
    $@
    set +x
}

out_dir=segmented

# jvs_music
xrun python gather_wavs.py \
    ../db/jvs_music_ver1 \
    --prefix jvs_music \
    --out_dir $out_dir/jvs_music_ver1 \
    --vad --run
