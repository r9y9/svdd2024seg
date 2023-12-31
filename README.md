# svdd2024seg

Tools to perform segmentation for long singing voice recordings.

## Requirements

- Python 3.8+
- [Poetry](https://python-poetry.org/)

## List of DBs

| DB                     | URL                                                                         |
|------------------------|-----------------------------------------------------------------------------|
| kiritan_singing        | https://zunko.jp/kiridev/login.php                                          |
| ofuton_p_utagoe_db     | https://sites.google.com/view/oftn-utagoedb/%E3%83%9B%E3%83%BC%E3%83%A0     |
| oniku_kurumi_utagoe_db | https://onikuru.info/db-download/                                           |
| jvs_music_ver1         | https://sites.google.com/site/shinnosuketakamichi/research-topics/jvs_music |

## Setup

Please do make sure to install poetry first. Then, clone this repository and install the dependencies.

```shell
git clone git@github.com:r9y9/svdd2024seg.git
cd svdd2024seg
git submodule update --init --recursive
poetry install
```

Tp perform segmetnation, put the singing DBs in the `db` directory. You must have the following directory structure before running the script:

```
$ tree -L 2 db
db
├── OFUTON_P_UTAGOE_DB
├── ONIKU_KURUMI_UTAGOE_DB
├── jvs_music_ver1
└── kiritan_singing
```

You are now ready to go.

## Usage

```shell
./runall.sh
```

You'll see the following outputs after the script finishes:

```
jvs_music_ver1
  2765 files
kiritan_singing
  525 files
ofuton_p_utagoe_db
  394 files
oniku_kurumi_utagoe_db
  451 files
```

You can find segmented wav files in the `segmented_all` directory.

```shell
$ tree -L 1 segmented_all
segmented_all
├── jvs_music_ver1
├── kiritan_singing
├── ofuton_p_utagoe_db
└── oniku_kurumi_utagoe_db
```
