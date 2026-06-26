cmake_minimum_required(VERSION 3.8)
project(realsense_d435i)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(realsense2 REQUIRED)
find_package(OpenCV REQUIRED)

add_executable(video_stream_node src/video_stream_node.cpp)

# Target Include Directories
# target_include_directories(video_stream_node PRIVATE
#   ${rclcpp_INCLUDE_DIRS}
#   ${sensor_msgs_INCLUDE_DIRS}
#   ${cv_bridge_INCLUDE_DIRS}
#   ${realsense2_INCLUDE_DIRS}
#   ${OpenCV_INCLUDE_DIRS}
# )

# Link Libraries
target_link_libraries(video_stream_node
  rclcpp::rclcpp
  sensor_msgs::sensor_msgs_library
  cv_bridge::cv_bridge
  ${realsense2_LIBRARY}
  ${OpenCV_LIBRARIES}
)

# Install rules
install(TARGETS
  video_stream_node
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
