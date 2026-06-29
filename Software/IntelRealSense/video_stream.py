import os
import cv2
import numpy as np
import pyrealsense2 as rs

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_FPS = 30


def main():
    print("[CAMERA] Starting Intel RealSense D435i stream...")
    pipeline = rs.pipeline()
    config = rs.config()

    # 1. Enable BOTH color and depth streams with matching dimensions and frame rate
    config.enable_stream(rs.stream.color, FRAME_WIDTH, FRAME_HEIGHT, rs.format.bgr8, FRAME_FPS)
    config.enable_stream(rs.stream.depth, FRAME_WIDTH, FRAME_HEIGHT, rs.format.z16, FRAME_FPS)
    
    # Start the camera pipeline with our configuration
    pipeline.start(config)

    # 2. Setup Alignment & Colorization Utility
    # We align the depth frame to match the color frame's coordinate perspective
    align_to = rs.stream.color
    align = rs.align(align_to)
    
    # This colorizer converts raw 16-bit depth values into a beautiful 8-bit color map automatically
    colorizer = rs.colorizer()

    np.random.seed(42)
    colors = np.random.randint(0, 255, size=(100, 3), dtype=np.uint8)
    print("[SYSTEM] Perception loop running. Focus the OpenCV window and press 'q' to shut down.")
    
    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())
            
            depth_color_frame = colorizer.colorize(depth_frame)
            depth_image = np.asanyarray(depth_color_frame.get_data())
            
            cv2.imshow("Color Image", color_image)
            cv2.imshow("Depth Image", depth_image)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        print("[CAMERA] Shutting down streams and cleaning up system environment...")
        pipeline.stop()
        cv2.destroyAllWindows()
        print("[SYSTEM] Exit completed cleanly.")


if __name__ == "__main__":
    main()