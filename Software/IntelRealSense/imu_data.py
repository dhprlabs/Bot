import pyrealsense2 as rs

# Setup pipeline and enable IMU streams
print("[CAMERA] Starting Intel RealSense D435i stream...")
pipeline = rs.pipeline()
config = rs.config()

config.enable_stream(rs.stream.accel, rs.format.motion_xyz32f, 200)
config.enable_stream(rs.stream.gyro, rs.format.motion_xyz32f, 200)

pipeline.start(config)

try:
    while True:
        frames = pipeline.wait_for_frames()

        if acc := frames.first_or_default(rs.stream.accel):
            a = acc.as_motion_frame().get_motion_data()
            print(f"Accel: x={a.x:.2f}, y={a.y:.2f}, z={a.z:.2f}")

        if gyro := frames.first_or_default(rs.stream.gyro):
            g = gyro.as_motion_frame().get_motion_data()
            print(f"Gyro: x={g.x:.2f}, y={g.y:.2f}, z={g.z:.2f}")


except KeyboardInterrupt:
    pipeline.stop()