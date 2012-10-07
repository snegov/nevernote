#!/bin/bash

if [ -z "$1" ]; then
	exit
fi
URL=$1

if [ -n "$2" ]; then
	NOTEBOOK=$2
else
	NOTEBOOK='read'
fi

TODO='no'
if [ -n "$3" ]; then
	echo $3 | grep todo > /dev/null 2>&1
	if [ "$?" -eq 0 ]; then
		TODO='yes'
	fi
fi

mkdir -p $HOME/.nevernote
TMP_DIR=`mktemp -d $HOME/.nevernote/nevernote.XXXXXX`
NEVERNOTE_DIR="/mnt/tabula/nevernote/$NOTEBOOK"
TODO_DIR="/mnt/tabula/nevernote/todo"

## Take page title
echo
echo `date '+%H:%M:%S'`
echo $URL

## Check if URL is forbidden to download
grep -x "$URL" $HOME/.nevernote/nevernote-list-excluded > /dev/null 2>&1
if [ "$?" -eq 0 ]; then
	echo "exclude"
	echo $URL >> $HOME/.nevernote/nevernote-error-excluded
	rm -r $TMP_DIR
	exit
fi

## Check if it is downloading now
#ps ax | grep "./scripts/nevernote.sh" | awk '{print($7)}' | grep -x "$URL"
#if [ "$?" -eq 0 ]; then
#	echo "downloading now"
#	rm -r $TMP_DIR
#	exit
#fi

## Check downloaded urls for duplicates
#head -qn 1 ${NEVERNOTE_DIR}/*/wget.log | awk '{print($3)}' | grep -x "$URL" > /dev/null 2>&1
grep -x "$URL" $HOME/.nevernote/nevernote-list-downloaded > /dev/null 2>&1
if [ "$?" -eq 0 ]; then
	echo "dublicate"
	echo $URL >> $HOME/.nevernote/nevernote-error-dups
	rm -r $TMP_DIR
	exit
fi

wget -T 15 -t 5 --user-agent="" -P $TMP_DIR "$URL" > /dev/null 2>&1
INDEX_PAGE=`ls $TMP_DIR`
if [ "$INDEX_PAGE" = '' ]; then
	echo "download error"
	echo $URL >> $HOME/.nevernote/nevernote-error-404
	rm -r $TMP_DIR
	exit
fi

## Convert page to system's charset
enconv "$TMP_DIR/$INDEX_PAGE" > /dev/null 2>&1

## Remove RC and LF symbols
#tr -d '\n' < "$TMP_DIR/$INDEX_PAGE" | tr -d '\r' > "$TMP_DIR/${INDEX_PAGE}.plain"
#mv "$TMP_DIR/${INDEX_PAGE}.plain" "$TMP_DIR/$INDEX_PAGE"

## Extract title and leave non-destruct chars
PAGE_DIR=$(sed -n -e 's/.*<title>\(.*\)<\/title>.*/\1/p' "$TMP_DIR/$INDEX_PAGE" | sed 's+[\+\{\;\"\\\=\?~\(\)\<\>\&\*\|\$\/\#:]+_+g')
PAGE_DIR=$(echo $PAGE_DIR | sed 's+\.*$++g')

## Remove first and last whitespaces
PAGE_DIR=$(echo $PAGE_DIR | sed 's+^ *++g' | sed 's+ *$++g')

## Trunc too long titles
if [ "${#PAGE_DIR}" -gt 100 ]; then
	PAGE_DIR=${PAGE_DIR:0:100}
fi

## If title wasn't parsed, leave random name
if [ "$PAGE_DIR" = '' ]; then
	PAGE_DIR=`basename $TMP_DIR`
fi
rm "$TMP_DIR/$INDEX_PAGE"

## Check local storage folder
## If duplicate - rename (add "_dup.X" to the end)
while true; do
	ls "$NEVERNOTE_DIR/$PAGE_DIR" > /dev/null 2>&1
	if [ "$?" -eq 0 ]; then
		DUP=${PAGE_DIR#*_dup.}
		if [ "$DUP" = "$PAGE_DIR" ]; then
			DUP=1
		else
			let "DUP += 1"
		fi
		PAGE_DIR=${PAGE_DIR%_dup.*}"_dup."$DUP
	else
		break
	fi
done

## Download full page
wget -E -H -k -K -p -e robots=off --user-agent="" -T 15 -t 5 -nd -o $TMP_DIR/wget.log -P $TMP_DIR "$URL"
WGET_EXIT_CODE=$?
if [ "$WGET_EXIT_CODE" -ne 0 ]; then
	echo $WGET_EXIT_CODE"|"$URL >> $HOME/.nevernote/nevernote-error-wget
fi

## Make link for index.html
#pushd $TMP_DIR > /dev/null 2>&1
#INDEX_PATH=`find ./ -name "${INDEX_PAGE}.orig"`
#ln -s "${INDEX_PATH%.orig}" "$INDEX_PAGE" > /dev/null 2>&1
#if [ "$?" -ne 0 ]; then
#	echo Cant\'t link $URL
#	echo $URL >> $HOME/.nevernote/nevernote-errors
#	rm -r $TMP_DIR
#	exit
#fi
#popd > /dev/null 2>&1

## Save page url
echo $URL > $TMP_DIR/URL

mv $TMP_DIR "$NEVERNOTE_DIR/$PAGE_DIR"
echo "saved in $NEVERNOTE_DIR/$PAGE_DIR"
if [ "$TODO" = "yes" ]; then
	ln -s "$NEVERNOTE_DIR/$PAGE_DIR" $TODO_DIR
fi
echo $URL >> $HOME/.nevernote/nevernote-list-downloaded
