import threading

import rclpy
import numpy as np
import pyrealsense2 as rs

from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

# Depth=1, best-effort: for a real-time feed into a model, you always
# want the FRESHEST frame, not a queue of stale ones. qos_profile_sensor_data
# defaults to a depth of 5, which lets frames back up if the subscriber
# (e.g. your segmentation model) is momentarily slower than the camera.
IMAGE_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)


class VideoStream(Node):
    def __init__(self):
        super().__init__('video_stream_node')

        self.frame_width = 640
        self.frame_height = 480
        self.frame_fps = 60

        # Set to True only if you actually need a colorized depth topic
        # for viewing purposes. It costs real CPU time per frame.
        self.publish_colorized_depth = False

        self.br = CvBridge()
        self.init_camera()

        # Sensor-data QoS (best-effort, small depth) is the correct
        # profile for camera streams. Reliable QoS (the default) causes
        # retransmission/backpressure that shows up as visible lag in
        # image viewers, especially over Wi-Fi or under CPU load.
        self.color_pub = self.create_publisher(
            Image, 'camera/color/image_raw', IMAGE_QOS)
        self.depth_pub = self.create_publisher(
            Image, 'camera/depth/image_rect_raw', IMAGE_QOS)

        if self.publish_colorized_depth:
            self.depth_color_pub = self.create_publisher(
                Image, 'camera/depth/image_colorized', IMAGE_QOS)

        # Frame capture runs in its own background thread using the
        # BLOCKING wait_for_frames() call, completely decoupled from
        # ROS's timer/executor. This is the standard pattern for camera
        # drivers: the thread naturally paces itself to the camera's
        # real frame rate, with no independent timer fighting it and
        # no unreliable non-blocking polling that can silently return
        # empty framesets forever.
        self._running = True
        self._capture_thread = threading.Thread(
            target=self.capture_loop, daemon=True)
        self._capture_thread.start()

        self.get_logger().info('[CAMERA]: Starting Intel RealSense D435i stream...')

    def init_camera(self):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(
            rs.stream.color, self.frame_width, self.frame_height,
            rs.format.bgr8, self.frame_fps)
        self.config.enable_stream(
            rs.stream.depth, self.frame_width, self.frame_height,
            rs.format.z16, self.frame_fps)

        self.profile = self.pipeline.start(self.config)

        # RealSense color sensors default to "auto exposure priority",
        # which lets the camera silently STRETCH exposure time (and
        # therefore drop below your requested fps) in low light. For a
        # locked, consistent 60fps feed — important for a model
        # expecting steady frame timing — disable this.
        color_sensor = self.profile.get_device().first_color_sensor()
        if color_sensor.supports(rs.option.auto_exposure_priority):
            color_sensor.set_option(rs.option.auto_exposure_priority, 0)

        align_to = rs.stream.color
        self.align = rs.align(align_to)

        if self.publish_colorized_depth:
            self.colorizer = rs.colorizer()

    def capture_loop(self):
        # Runs on the background thread for the lifetime of the node.
        # wait_for_frames() blocks until the camera actually has a new
        # frame ready, so this loop paces itself at the camera's true
        # frame rate with no separate timer to fall out of sync with.
        while self._running and rclpy.ok():
            try:
                frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            except RuntimeError:
                # Timed out waiting for a frame (e.g. USB hiccup).
                # Log and keep trying rather than crashing the thread.
                self.get_logger().warn(
                    '[CAMERA]: Timed out waiting for frames, retrying...')
                continue

            aligned_frames = self.align.process(frames)
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()

            if not color_frame or not depth_frame:
                self.get_logger().warn('[CAMERA]: Dropped an incomplete frame set.')
                continue

            stamp = self.get_clock().now().to_msg()

            # --- Color image ---
            color_image = np.asanyarray(color_frame.get_data())
            color_msg = self.br.cv2_to_imgmsg(color_image, encoding='bgr8')
            color_msg.header.stamp = stamp
            color_msg.header.frame_id = 'camera_color_optical_frame'

            # --- Depth image (raw 16-bit, in millimeters) ---
            # Publishing raw depth is far cheaper than colorizing every
            # frame, and is what most downstream nodes (point cloud,
            # obstacle detection, etc.) actually want.
            depth_image = np.asanyarray(depth_frame.get_data())
            depth_msg = self.br.cv2_to_imgmsg(depth_image, encoding='16UC1')
            depth_msg.header.stamp = stamp
            depth_msg.header.frame_id = 'camera_depth_optical_frame'

            # Publishing can race with Ctrl+C: rclpy's SIGINT handling
            # can invalidate the context mid-loop, between the rclpy.ok()
            # check above and the actual publish call below. That's a
            # normal, harmless shutdown race — swallow it quietly rather
            # than let it print a scary (but benign) traceback.
            try:
                self.color_pub.publish(color_msg)
                self.depth_pub.publish(depth_msg)

                # --- Optional colorized depth, only if explicitly enabled ---
                if self.publish_colorized_depth:
                    depth_color_frame = self.colorizer.colorize(depth_frame)
                    depth_color_image = np.asanyarray(depth_color_frame.get_data())
                    depth_color_msg = self.br.cv2_to_imgmsg(depth_color_image, encoding='bgr8')
                    depth_color_msg.header.stamp = stamp
                    depth_color_msg.header.frame_id = 'camera_depth_optical_frame'
                    self.depth_color_pub.publish(depth_color_msg)
            except rclpy.executors.ExternalShutdownException:
                break
            except Exception:
                if rclpy.ok():
                    raise
                break

    def destroy_node(self):
        self._running = False
        self._capture_thread.join(timeout=2.0)
        self.pipeline.stop()
        self.get_logger().info(
            "[CAMERA]: Shutting down streams and cleaning up system environment...")
        self.get_logger().info("[SYSTEM]: Exit completed cleanly.")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    vs_node = VideoStream()
    try:
        rclpy.spin(vs_node)
    except KeyboardInterrupt:
        pass
    finally:
        vs_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()