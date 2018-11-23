
pet=$1
out_fn=$2
if [[ ! -f $pet ]] ; then
    echo "Error: Could not find file $pet"
    exit 1
fi

time_width_str=`mincinfo -varvalue time-width $pet`
time_str=`mincinfo -varvalue time $pet`
header_unit=`mincinfo -attvalue  time:units $pet`
radio=`mincinfo -attvalue acquisition:radionuclide $pet`
hl=`mincinfo -attvalue acquisition:radionuclide_halflife $pet`


if [[ $radio == "" ]] ; then
    echo "Error could not find radionuclide in $pet"
    exit 1
fi

if [[ $hl == "" ]] ; then
    echo "Warning: could not find radionuclide_halflife in $pet"
fi
if [[ "$header_unit" == "seconds" || "$header_unit" == "Seconds" || "$header_unit" == "sec" || "$header_unit" == "s" ]]; then
    unit="s"
elif  [[ "$header_unit" == "minutes" || "$header_unit" == "Minutes" || "$header_unit" == "min"|| "$header_unit" == "m" ]]; then
    unit="m"
else
    echo "Error could not find time unit for $pet"
fi


IFS=' ' read -r -a time <<< $time_str
IFS=' ' read -r -a time_width <<< $time_width_str

out_str="{\n\t\"Info\":{\"Isotope\":\"${radio}\",\"Halflife\":${hl}},\n\t\"Time\" : {\n\t\t\"FrameTimes\": {\n\t\t\t\"Units\": [\"$unit\", \"$unit\"],\n\t\t\t\"Values\":[\n"

for index in  "${!time[@]}"; do
    let index0=${index}+1
    t2=`python -c "print(${time_width[index]}+${time[index]})"`
    out_str="${out_str}\t\t\t[${time[index]}, $t2]"
    if [[ ! "$index0" == "${#time[@]}" ]]; then
        out_str="$out_str,"
    else
        out_str="${out_str}]"
    fi 
    out_str="${out_str}\n"
done
out_str="${out_str}\t\t}\n\t}\n}\n"
printf "$out_str" > $out_fn

