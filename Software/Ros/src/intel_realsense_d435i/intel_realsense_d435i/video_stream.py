import rclpy
import cv2
import pyrealsense2 as rs
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class VideoStream(Node):
    def __init__(self):
        super().__init__('video_stream_node')
        self.frame_width = 640
        self.frame_height = 480
        self.frame_fps = 30

        self.init_camera()

        self.publisher_ = self.create_publisher(Image, 'camera/color/image_raw', 10)
        timer_period = 1.0 / self.frame_fps  
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        self.br = CvBridge()
        self.get_logger().info('[CAMERA]: Starting Intel RealSense D435i stream...')

    def init_camera(self):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.color, self.frame_width, self.frame_height, rs.format.bgr8, self.frame_fps)
        self.config.enable_stream(rs.stream.depth, self.frame_width, self.frame_height, rs.format.z16, self.frame_fps)
        self.pipeline.start(self.config)

        align_to = rs.stream.color
        self.align = rs.align(align_to)
        self.colorizer = rs.colorizer()

    def timer_callback(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)
        
        color_frame = aligned_frames.get_color_frame()
        depth_frame = aligned_frames.get_depth_frame()

        color_image = np.asanyarray(color_frame.get_data())
        ros_color_image = self.br.cv2_to_imgmsg(color_image, encoding='bgr8')
        self.publisher_.publish(ros_color_image)

        depth_color_frame = self.colorizer.colorize(depth_frame)
        depth_image = np.asanyarray(depth_color_frame.get_data())

    def destroy_node(self):
        self.pipeline.stop()
        super().destroy_node()
        self.get_logger().info("[CAMERA]: Shutting down streams and cleaning up system environment...")
        self.get_logger().info("[SYSTEM]: Exit completed cleanly.")


def main(args=None):
    rclpy.init(args=args)
    vs_node = VideoStream()
    
    try:
        rclpy.spin(vs_node)
    except KeyboardInterrupt:
        pass
    finally:
        vs_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()