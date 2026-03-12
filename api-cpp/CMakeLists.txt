cmake_minimum_required(VERSION 3.15)
project(spotify_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_BUILD_TYPE Release)
add_compile_options(-O3 -march=native)

find_package(bsoncxx REQUIRED)
find_package(mongocxx REQUIRED)

find_package(Boost REQUIRED COMPONENTS context)
find_package(CURL REQUIRED)

add_executable(api main.cpp)

target_include_directories(api PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/lithium/single_headers)

target_link_libraries(api PRIVATE 
    mongo::mongocxx_shared 
    mongo::bsoncxx_shared 
    Boost::context
    CURL::libcurl
    pthread 
    ssl 
    crypto
    redis++
    hiredis
)
