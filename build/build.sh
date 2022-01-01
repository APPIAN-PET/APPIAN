cd base
    echo
    echo "Build Base"
    echo 
    docker build $1 . --tag tffunck/appian:base
cd ..

cd appian
    echo
    echo "Build APPIAN"
    echo 
    docker build --no-cache . --tag tffunck/appian:latest
cd ..
