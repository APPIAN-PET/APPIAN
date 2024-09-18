cd base
    echo "Build Base"
    docker build $1 . --tag stefancepa995/clario-appian:base
cd ..


cd appian
    echo "Build APPIAN"
    docker build --no-cache . --tag stefancepa995/clario-appian:latest
cd ..
