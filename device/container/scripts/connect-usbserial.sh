#!/bin/bash
#
# https://ss64.com/osx/screen.html
#

set -e

pkill SCREEN || :

devices=($(ls /dev/cu.usbserial-* 2> /dev/null | head -1))
[ -c '/dev/cu.SLAB_USBtoUART' ] && devices+=('/dev/cu.SLAB_USBtoUART')

if (( ${#devices[@]} == 0 )); then
  echo 'TTL device not found'
  exit 1
fi

echo

i=1
for device in "${devices[@]}"; do
  echo "${i}: ${device}"
  i=$((i+1))
done

read -p "Select a device above [1]: " input
  [ -z "${input}" ] && input=1
  if [[ ${input} ]] && [ ${input} -eq ${input} 2> /dev/null ] && (( ${input} <= ${#devices[@]} )); then
    echo "Using ${devices[((input-1))]}..."
    while true; do
      read -n 1 -p "Use 'CTRL-a k' to kill the screen session when ready. Press M to print shortcuts; Press ENTER to continue... " yn
        case $yn in
          [mM]* ) printf "

Ctrl+a c \t new window
Ctrl+a n \t next window
Ctrl+a p \t previous window
Ctrl+a \" \t select window from list
Ctrl+a Ctrl+a \t previous window viewed

Ctrl+a S \t split terminal horizontally into regions
Ctrl+a | \t split terminal vertically into regions
Ctrl+a :resize \t resize region
Ctrl+a :fit \t fit screen size to new terminal size
Ctrl+a :remove \t remove region
Ctrl+a tab \t Move to next region

Ctrl+a d \t detach screen from terminal
Ctrl+a A \t set window title
Ctrl+a x \t lock session
Ctrl+a [ \t enter scrollback/copy mode
Ctrl+a ] \t paste buffer
Ctrl+a > \t write paste buffer to file
Ctrl+a < \t read paste buffer from file

Ctrl+a ? \t show key bindings/command names
Ctrl+a : \t goto screen command prompt

";;
          * ) break;;
        esac
    done
    screen -a -A ${devices[((input-1))]} 115200
  else
     echo "Invalid selection: ${input}"
  fi