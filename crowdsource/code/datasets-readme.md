cat FILE | xargs -n 1 -P 8 wget -bqc
md5sum -c checksums.txt

for FNAME in `ls *.tar` ; do echo "$FNAME" ; done
for FNAME in `ls *.tar` ; do echo "$FNAME"; time tar -xvf $FNAME ;


ls *.tar | xargs -n 1 -P 8 tar -xvf
ls *.tgz | xargs -n 1 -P 8 tar -xvzf
