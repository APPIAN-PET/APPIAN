docker_path=$1
host_path=$2

for f in `find -L  -type l `; do
    new_link=`readlink $f | sed "s#$docker_path#$host_path#g"`
    if [[ -d $new_link ]]; then
         ln -fs $new_link ${f}
    else 
        echo "Error: could not find new link  < $new_link >  for $f"
    fi
done

