#!/bin/bash
#
# What is this?
# This script will deploy the build static files to a Github account
# using the gh-pages branch for Github Pages.
#
# The data APIs will use static files stored under <project-root>/web/public/demo
#
# How do I use it?
# $ bash <project-root>/scripts/web-deploy-github-pages.sh -r <git-repo> [-m <commit-message>] [--amend]
# -r <git-repo>  ......... the github repo url used when cloning (i.e. git@github.com:UserName/aws-iot-baseline.git)
# -m <commit-message>  ... the git commit message
# --amend  ............... amend the previous commit instead of a new message

set -e

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script_path=${script_dir}/$(basename "${BASH_SOURCE[0]}")
script_name=$(basename ${BASH_SOURCE[0]})

git_repo=$(git remote -v | grep github.com | tail -n1 | awk '{print $2}')
git_message=
git_amend=

while test $# -gt 0; do
  case "$1" in
    -r) git_repo="$2"; shift;;
    -m) git_message="$2"; shift;;
    --amend) git_message=0; git_amend=1;;
    *) >&2 echo "Bad argument $1"; exit 1;;
  esac
  shift
done

if [ -z "${git_repo}" ] || [ -z "${git_message}" ]; then
  >&2 echo "Usage: ${script_name} -r <git-repo> [--amend] [-m <commit-message>]"
  exit 1
fi

root_dir=$(cd "${script_dir}/../.." && pwd)
web_dir=${root_dir}/web
build_dir=${root_dir}/.build

function toolchain_require() { [ -n "$(command -v $1)" ] && return 0 || >&2 echo "$1: not found"; return 1; }
toolchain_require git
toolchain_require rsync
toolchain_require npm

rm -rf "${build_dir}/gh-pages"

rm -rf "${build_dir}/gh-pages-tmp"
mkdir "${build_dir}/gh-pages-tmp"

cd "${web_dir}"

npm install

github_user=$(echo ${git_repo} | sed -n "s/^.*@github\.com:\(.*\)\/\(.*\)\.git/\1/p" | tr '[:upper:]' '[:lower:]')
github_project=$(echo ${git_repo} | sed -n "s/^.*@github\.com:\(.*\)\/\(.*\)\.git/\2/p")

echo "Using github page: https://${github_user}.github.io/${github_project}"

PUBLIC_URL="/${github_project}" \
REACT_APP_API_URL="/${github_project}/demo" \
REACT_APP_ROUTER_CLASS="HashRouter" \
npm run build

git clone --single-branch --branch gh-pages ${git_repo} "${build_dir}/gh-pages"

rsync -av --del --exclude='.git' build/ "${build_dir}/gh-pages/"

git -C "${build_dir}/gh-pages" add .

if (( ${git_amend} )); then
  git -C "${build_dir}/gh-pages" commit --amend --no-edit
  git -C "${build_dir}/gh-pages" push --force
else
  git -C "${build_dir}/gh-pages" commit -m "${git_message}"
  git -C "${build_dir}/gh-pages" push
fi