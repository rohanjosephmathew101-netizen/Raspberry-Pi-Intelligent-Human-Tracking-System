import smbus

bus = smbus.SMBus(1)

for device in range(0x03, 0x78):
    try:
        bus.read_byte(device)
        print(f"Found device at address: 0x{device:02X}")
    except:
        pass
