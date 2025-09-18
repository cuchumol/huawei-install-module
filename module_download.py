import pandas as pd
import netmiko
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
import ftputil
import yaml
from getpass import getpass
from dotenv import load_dotenv
from jinja2 import Template
import os


load_dotenv()
ftp_user = os.getenv("FTP_USER")
ftp_password = os.getenv("FTP_PASSWORD")
module_file = os.getenv("MODULE_FILE")
remote_directory = os.getenv("REMOTE_DIRECTORY")

    
user = input("Input user: ")
password = getpass("Input password: ")


filename = ""



def load_template(file_template, **kwargs):
    with open(file_template, 'r') as f:
        template_content = f.read()
    template = Template(template_content)
    rendered = template.render(**kwargs)
    return rendered.splitlines()




ftp_user_config_commands = load_template('templates/ftp_user.txt', ftp_user=ftp_user, ftp_password=ftp_password)
undo_ftp_user_config_commands = load_template('templates/undo_ftp_user.txt', ftp_user=ftp_user)




def install_module(hostname, ip):
    
    
    parameters = {
        'device_type': 'huawei',
        'host': ip,
        'username': user,
        'password': password,
        'port': 22,
        'session_log': f'logs/{hostname}.txt'
    }


    is_exeption = False
    try:
        connection = netmiko.ConnectHandler(**parameters)

        print(f"{hostname} ({ip}) connect successfully")


        # add ftp config
        connection.enable()
        
        output = connection.send_config_set(ftp_user_config_commands, cmd_verify=False)

        if 'error' in output.lower():
            print(f"{hostname} ({ip}) cannot commit ftp config\n")
            connection.disconnect()

            return


        # ftp load file
        try:
            with ftputil.FTPHost(ip, ftp_user, ftp_password) as host:
                host.upload(module_file, f"{remote_directory}/{module_file}")
        except Exception as e:
            print(f"\n{hostname} ({ip}) except Exception during transmission file : {e}")
            is_exeption = True


        # module activation
        if not is_exeption:

            output = connection.send_command(f'install-module {module_file}')
            output = output.split('\n')[-1].split(':')[-1].strip()
            print(f"{hostname} ({ip}) : {output}")
            if 'Succeeded' in output:
                output = connection.send_command(f'install-module {module_file} next-startup')
                output = output.split('\n')[-1].split(':')[-1].strip()

                print(f"{hostname} ({ip}) : {output}")


        # delete ftp config
        output = connection.send_config_set(undo_ftp_user_config_commands, cmd_verify=False)

        if 'error' in output.lower():
            print(f"\n{hostname} ({ip}) cannot commit undo ftp config\n")
        

        connection.disconnect()
    except Exception as exp:
        print(f'Exception during connection {hostname} ({ip})')
        print(exp)
    
    print(f"{hostname} ({ip}) disconnect")




if __name__ == '__main__':
    
    df = pd.read_excel(f"device_tables/{filename}.xls")

    if input("Continue (y/n)? ").lower() == 'y':

        with ThreadPoolExecutor(max_workers=8) as executor:
                future_list = [executor.submit(install_module, row['Hostname'], row['Ip-Address-With-Mask'].split('/')[0]) for _, row in df.iterrows()]
                wait(future_list, return_when=ALL_COMPLETED)