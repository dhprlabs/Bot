#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

# Import your custom module
from st3215 import ST3215
    
class DriverNode(Node):
    def __init__(self):
        super().__init__('driver_node')
        
        # Declare parameters for configuration
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('left_motor_id', 1)
        self.declare_parameter('right_motor_id', 2)
        self.declare_parameter('max_speed_scale', 1500) # Mapping factor for incoming velocity commands
        
        port = self.get_parameter('port').get_parameter_value().string_value
        self.left_id = self.get_parameter('left_motor_id').get_parameter_value().integer_value
        self.right_id = self.get_parameter('right_motor_id').get_parameter_value().integer_value
        self.speed_scale = self.get_parameter('max_speed_scale').get_parameter_value().integer_value
        
        self.get_logger().info(f"Initializing ST3215 driver on port: {port}")
        
        try:
            # Initialize ST3215 serial handler
            self.servo = ST3215(port)
        except Exception as e:
            self.get_logger().error(f"Failed to open port {port}: {str(e)}")
            raise e

        # Ensure motors are in continuous speed mode (Mode 1)
        self.servo.SetMode(self.left_id, 1)
        self.servo.SetMode(self.right_id, 1)
        
        # Enable Torques
        self.servo.StartServo(self.left_id)
        self.servo.StartServo(self.right_id)
        
        # Subscribers & Publishers
        self.cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.telemetry_pub = self.create_publisher(Float32MultiArray, '~/telemetry', 10)
        
        # Status Telemetry Loop (Runs at 1 Hz to avoid overloading serial bus)
        self.telemetry_timer = self.create_timer(1.0, self.publish_telemetry)
        self.get_logger().info("ST3215 ROS 2 Driver operational. Listening to /cmd_vel")

    def cmd_vel_callback(self, msg: Twist):
        # We only look at linear.x for forward/backward motions
        linear_x = msg.linear.x
        
        # Scale command velocity to your target step speed limits
        target_speed = int(linear_x * self.speed_scale)
        
        # If running a standard differential configuration setup:
        # One motor spins inverted structurally relative to the opposing frame orientation
        left_speed = target_speed
        right_speed = -target_speed 
        
        # Command continuous rotation to both servo interfaces
        self.servo.Rotate(self.left_id, left_speed)
        self.servo.Rotate(self.right_id, right_speed)

    def publish_telemetry(self):
        # Read parameters from first servo unit to log hardware metrics safely
        v1 = self.servo.ReadVoltage(self.left_id)
        c1 = self.servo.ReadCurrent(self.left_id)
        t1 = self.servo.ReadTemperature(self.left_id)
        
        # Fallbacks for empty packets or read drops
        v1 = v1 if v1 is not None else 0.0
        c1 = c1 if c1 is not None else 0.0
        t1 = float(t1) if t1 is not None else 0.0
        
        msg = Float32MultiArray()
        msg.data = [v1, c1, t1]
        self.telemetry_pub.publish(msg)

    def destroy_node(self):
        # Gracefully halt motors upon Node shutdown sequence signals
        self.servo.Rotate(self.left_id, 0)
        self.servo.Rotate(self.right_id, 0)
        self.servo.StopServo(self.left_id)
        self.servo.StopServo(self.right_id)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    try:
        node = DriverNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()