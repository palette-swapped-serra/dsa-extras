@echo off
pushd %~dp0
mkdir fe7
cd fe7
dsd -l sys -p ..\..\dsa_extras\library -t fe7 "%FE7%" 0xb808ac:Text text.txt
dsd -l sys -p ..\..\dsa_extras\library -t fe7 "%FE7%" 0:Events events.txt
dsd -l sys -p ..\..\dsa_extras\library -t fe7 "%FE7%" 0:Misc result.txt
cd ..
mkdir fe8
cd fe8
dsd -l sys -p ..\..\dsa_extras\library -t fe8 "%FE8%" 0x15d48c:Text text.txt
dsd -l sys -p ..\..\dsa_extras\library -t fe8 "%FE8%" 0:Events events.txt
dsd -l sys -p ..\..\dsa_extras\library -t fe8 "%FE8%" 0:Misc misc.txt
cd ..
popd
