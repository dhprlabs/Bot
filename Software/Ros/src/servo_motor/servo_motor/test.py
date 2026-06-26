from st3215 import ST3215

servo = ST3215('/dev/ttyACM0')

servo.ChangeId(1, 2)
print("ID updated to 2!")

result_1 = servo.PingServo(1)
print(f'ping result_1: {result_1}')
result_2 = servo.PingServo(2)
print(f'ping result_2: {result_2}')

# voltage = servo.ReadVoltage(1)
# current = servo.ReadCurrent(1)
# print(f'voltage: {voltage}')
# print(f'current: {current}')

# temp = servo.ReadTemperature(1)
# print(f'temperature: {temp}')

# servo.SetMode(1, 1)
# servo.MoveTo(1, position=0, speed=1500)
