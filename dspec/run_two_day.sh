#!/bin/bash
echo "Running lwa update script"
touch /data1/pzhang/update_lwaspectra
/home/pz47/miniconda3/bin/activate lwa
/home/pz47/miniconda3/envs/lwa/bin/python3 /data1/pzhang/lwasolarview/generate_all_spectra.py --lasttwoday
