#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <cv_bridge/cv_bridge.hpp>
#include <librealsense2/rs.hpp>
#include <opencv2/opencv.hpp>


class VideoStream : public rclcpp::Node {
public:
    VideoStream() : Node("video_stream_node"), frame_width_(640), frame_height_(480), frame_fps_(30) {
        
        init_camera();

        // Create publisher for color image
        publisher_ = this->create_publisher<sensor_msgs::msg::Image>("camera/color/image_raw", 10);
        
        // Timer for frame pumping (30 FPS -> ~33.3ms)
        std::chrono::duration<double> timer_period(1.0 / frame_fps_);
        timer_ = this->create_wall_timer(timer_period, std::bind(&VideoStream::timer_callback, this));
        
        RCLCPP_INFO(this->get_logger(), "[CAMERA]: Starting Intel RealSense D435i stream in C++...");
    }

    ~VideoStream() {
        cleanup();
    }

private:
    void init_camera() {
        // Configure streams
        cfg_.enable_stream(RS2_STREAM_COLOR, frame_width_, frame_height_, RS2_FORMAT_BGR8, frame_fps_);
        cfg_.enable_stream(RS2_STREAM_DEPTH, frame_width_, frame_height_, RS2_FORMAT_Z16, frame_fps_);
        
        // Start pipeline
        pipe_.start(cfg_);

        // Initialize alignment and colorizer objects
        align_ = std::make_unique<rs2::align>(RS2_STREAM_COLOR);
        colorizer_ = std::make_unique<rs2::colorizer>();
    }

    void timer_callback() {
        try {
            // Wait for frameset
            rs2::frameset frames = pipe_.wait_for_frames();
            
            // Align frameset to color
            rs2::frameset aligned_frames = align_->process(frames);
            
            rs2::video_frame color_frame = aligned_frames.get_color_frame();
            rs2::depth_frame depth_frame = aligned_frames.get_depth_frame();

            if (!color_frame || !depth_frame) {
                return;
            }

            // Convert RealSense frame to OpenCV Mat (Zero-copy wrapping of memory pointer)
            cv::Mat color_image(cv::Size(frame_width_, frame_height_), CV_8UC3, (void*)color_frame.get_data(), cv::Mat::AUTO_STEP);
            
            // Convert OpenCV Mat to ROS 2 Image Message
            std_msgs::msg::Header header;
            header.stamp = this->now();
            header.frame_id = "camera_color_optical_frame";
            auto ros_color_msg = cv_bridge::CvImage(header, "bgr8", color_image).toImageMsg();
            publisher_->publish(*ros_color_msg);

            // Equivalent to colorizer.colorize(depth_frame) in python
            rs2::video_frame depth_color_frame = colorizer_->colorize(depth_frame);
            cv::Mat depth_image(cv::Size(frame_width_, frame_height_), CV_8UC3, (void*)depth_color_frame.get_data(), cv::Mat::AUTO_STEP);
            

        } catch (const rs2::error & e) {
            RCLCPP_ERROR(this->get_logger(), "RealSense error calling %s(%s): %s", e.get_failed_function().c_str(), e.get_failed_args().c_str(), e.what());
        } catch (const std::exception & e) {
            RCLCPP_ERROR(this->get_logger(), "Standard exception: %s", e.what());
        }
    }

    void cleanup() {
        RCLCPP_INFO(this->get_logger(), "[CAMERA]: Shutting down streams and cleaning up system environment...");
        try {
            pipe_.stop();
        } catch (...) {}
        RCLCPP_INFO(this->get_logger(), "[SYSTEM]: Exit completed cleanly.");
    }

    // Parameters
    int frame_width_;
    int frame_height_;
    int frame_fps_;

    // RealSense components
    rs2::pipeline pipe_;
    rs2::config cfg_;
    std::unique_ptr<rs2::align> align_;
    std::unique_ptr<rs2::colorizer> colorizer_;

    // ROS 2 components
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<VideoStream>();
    
    try {
        rclcpp::spin(node);
    } catch (const std::size_t&) {}
    
    rclcpp::shutdown();
    return 0;
}