import pandas as pd
import netmiko
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from getpass import getpass
import os
from dotenv import load_dotenv


user = input("Input user: ")
password = getpass("Input password: ")

load_dotenv()
module_file = os.getenv("MODULE_FILE")

filename = ""


def get_module_info(hostname, ip):
    parameters = {
        'device_type': 'huawei',
        'host': ip,
        'username': user,
        'password': password,
        'port': 22,
        'session_log': f'logs/{hostname}.txt'
    }


    result = {
        'hostname': hostname,
        'ip': ip,
        'install': False,
        'next-startup': False
    }

    is_exeption = False
    try:
        connection = netmiko.ConnectHandler(**parameters)

        print(f"{hostname} ({ip}) connect successfully")


        if not is_exeption:

            output = connection.send_command(f'display module-information')
            if module_file in output:
                result['install'] = True
            
            
            
            output = connection.send_command(f'display module-information next-startup')
            if module_file in output:
                result['next-startup'] = True


        connection.disconnect()
    except Exception as exp:
        print(f'Exception during connection {hostname} ({ip})')
        print(exp)
    
    print(f"{hostname} ({ip}) disconnect")

    return result


if __name__ == '__main__':
    
    os.makedirs("result_tables", exist_ok=True)
    os.makedirs("logs", exist_ok=True)


    df = pd.read_excel(f"device_tables/{filename}.xls")

    if not os.path.exists(module_file):
        print(f"Module file {module_file} not found")
    
    
    elif input('Continue?').lower() == 'y':

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_list = [executor.submit(get_module_info, row['Sysname'], row['MgntIPv4-With-Mask'].split('/')[0]) for _, row in df.iterrows()]
            wait(future_list, return_when=ALL_COMPLETED)

        results = [future.result() for future in future_list]

        df1 = pd. DataFrame(results)
        df1.to_excel(f"result_tables/{filename}.xlsx", index=False)