import threading
from uf_robot_umi_teleop import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='configuration args')
    parser.add_argument('-c', '--config', type=str, required=True, 
                       help='configuration file path, e.g.my_config.yaml')
    args = parser.parse_args()
    try:
        with open(Path(args.config).expanduser(), 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config yaml file: {e}")

    left_config = config["L"]
    right_config = config["R"]

    def run(teleop):
        teleop.run()

    robot_confg1 = UFRobotConfig(**left_config['RobotConfig'])
    teleop_confg1 = UmiTeleopConfig(**left_config['TeleoperatorConfig'])
    robot_confg2 = UFRobotConfig(**right_config['RobotConfig'])
    teleop_confg2 = UmiTeleopConfig(**right_config['TeleoperatorConfig'])
    teleop1 = UFRobotTeleop(teleop_confg1, robot_confg1)
    teleop2 = UFRobotTeleop(teleop_confg2, robot_confg2)

    t1 = threading.Thread(target=run, args=(teleop1,), daemon=True)
    t2 = threading.Thread(target=run, args=(teleop2,), daemon=True)
    
    t1.start()
    t2.start()

    time.sleep(1)

    print("\n********** Test Teleop With Robot **********")
    input('Enter to control robot with teleop >>> ')

    print("\n********** Teleop Control Loop Start **********")
    teleop1.set_status(1)
    teleop2.set_status(1)

    while True:
        time.sleep(1)