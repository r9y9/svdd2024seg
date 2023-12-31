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
NO2_ROOT=$NNSVS_ROOT/recipes/_common/no2
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
    echo "stage 0: Data preparation"
    sh $NO2_ROOT/utils/data_prep.sh ./config.yaml musicxml
    mkdir -p data/list

    echo "train/dev/eval split"
    find data/acoustic/ -type f -name "*.wav" -exec basename {} .wav \; \
        | sort > data/list/utt_list.txt

    # From ESPnet:
    # DEV_LIST = [
    #     "chatsumi",
    #     "my_grandfathers_clock_3_2",
    #     "haruyo_koi",
    #     "momiji",
    #     "tetsudou_shouka",
    # ]
    # TEST_LIST = [
    #     "usagito_kame",
    #     "my_grandfathers_clock_1_2",
    #     "antagata_dokosa",
    #     "momotarou",
    #     "furusato",
    # ]

    grep -e usagito_kame -e my_grandfathers_clock_1_2 -e antagata_dokosa -e momotarou -e furusato data/list/utt_list.txt > data/list/$eval_set.list
    grep -e chatsumi -e my_grandfathers_clock_3_2 -e haruyo_koi -e momiji -e tetsudou_shouka data/list/utt_list.txt > data/list/$dev_set.list
    grep -v -e usagito_kame -e my_grandfathers_clock_1_2 -e antagata_dokosa -e momotarou -e furusato -e chatsumi -e my_grandfathers_clock_3_2 -e haruyo_koi -e momiji -e tetsudou_shouka data/list/utt_list.txt > data/list/$train_set.list
fi
