#!/bin/bash

set -e
set -o pipefail

function xrun () {
    set -x
    $@
    set +x
}

db_root=$PWD/db/
outdir=$PWD/segmented_all

cd jvs_music_ver1
poetry run ./run.sh
cd -

cd kiritan_singing
poetry run ./run.sh --wav_root $db_root/kiritan_singing/wav --stage 0 --stop_stage 0
cd -

cd ofuton_p_utagoe_db
poetry run ./run.sh --stage 0 --stop_stage 0
cd -

cd oniku_kurumi_utagoe_db --stage 0 --stop_stage 0
poetry run ./run.sh
cd -

# Copy all the segmentated data into outdir
mkdir -p $outdir

# jvs
mkdir -p $outdir/jvs_music_ver1
cp -r jvs_music_ver1/segmented/jvs_music_ver1/* $outdir/jvs_music_ver1/
echo "jvs_music_ver1"
echo "  $(find $outdir/jvs_music_ver1 -name "*.wav" | wc -l) files"

# NNSVS datasets
for db in kiritan_singing ofuton_p_utagoe_db oniku_kurumi_utagoe_db
do
    mkdir -p $outdir/$db
    cp -r $db/data/acoustic/wav/* $outdir/$db/
    # show number of files
    echo "$db"
    echo "  $(find $outdir/$db -name "*.wav" | wc -l) files"
done
