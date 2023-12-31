#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

function xrun () {
    set -x
    $@
    set +x
}

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)
NNSVS_ROOT=$script_dir/../3rdparty/nnsvs
. $NNSVS_ROOT/utils/yaml_parser.sh || exit 1;

eval $(parse_yaml "./config.yaml" "")

train_set="train_no_dev"
dev_set="dev"
eval_set="eval"
datasets=($train_set $dev_set $eval_set)
testsets=($dev_set $eval_set)

stage=0
stop_stage=0

. $NNSVS_ROOT/utils/parse_options.sh || exit 1;

if [ ${stage} -le 0 ] && [ ${stop_stage} -ge 0 ]; then
    if [ ! -e downloads/kiritan_singing ]; then
        echo "stage -1: Downloading data"
        mkdir -p downloads
        git clone https://github.com/r9y9/kiritan_singing downloads/kiritan_singing
    fi
    echo "stage 0: Data preparation"
    kiritan_singing=downloads/kiritan_singing
    cd $kiritan_singing && git checkout .
    if [ ! -z "${wav_root}" ]; then
        echo "" >> config.py
        echo "wav_dir = \"$wav_root\"" >> config.py
    fi
    ./run.sh
    cd -
    mkdir -p data/list
    ln -sfn $PWD/$kiritan_singing/kiritan_singing_extra/timelag data/timelag
    ln -sfn $PWD/$kiritan_singing/kiritan_singing_extra/duration data/duration
    ln -sfn $PWD/$kiritan_singing/kiritan_singing_extra/acoustic data/acoustic

    echo "train/dev/eval split"
    find data/acoustic/ -type f -name "*.wav" -exec basename {} .wav \; \
        | sort > data/list/utt_list.txt
    # ESPnet
    # DEV_LIST = ["13", "14", "26", "28", "39"]
    # TEST_LIST = ["01", "16", "17", "27", "44"]

    grep -e 01_ -e 16_ -e 17_ -e 27_ -e 44_ data/list/utt_list.txt > data/list/$eval_set.list
    grep -e 13_ -e 14_ -e 26_ -e 28_ -e 39_ data/list/utt_list.txt > data/list/$dev_set.list
    grep -v -e 01_ -e 16_ -e 17_ -e 27_ -e 44_ -e 01_ -e 13_ -e 14_ -e 26_ -e 28_ -e 39_ data/list/utt_list.txt > data/list/$train_set.list
fi
