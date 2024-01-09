from time import sleep
from ahrs import AHRS

if __name__ == '__main__':
    print("Start")
    signal(SIGINT, handle_sig)
    with AHRS("/dev/ttyACM0") as com:
        print("Initializing")

        sleep(1)

        print("Pitch  |  Roll  |  Yaw  |  X-Accel  | Y-Accel  |  Z-Accel  |  Time  |")

        while True:
            print(com.pitch, com.roll, com.yaw, com.world_linear_accel_x, com.world_linear_accel_y, com.world_linear_accel_z)
            sleep(0.125)
            if sflag:
                break
        print("\nExit Caught... Closing device.\n")
    sleep(1)