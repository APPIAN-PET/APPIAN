cd base
    echo "Build Base"
    docker build $1 . --tag tffunck/appian:base
cd ..


cd appian
    echo "Build APPIAN"
    docker build --no-cache . --tag tffunck/appian:latest
cd ..
