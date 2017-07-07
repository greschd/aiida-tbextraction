if [ -d .aiida~ ]; then
    rm -r .aiida
    mv .aiida~ .aiida
fi
